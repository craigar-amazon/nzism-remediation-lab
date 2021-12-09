import logging
import json

import cfg.installer as cfginstall
import cfg.rules as cfgrules

from lib.rdq import Profile
from lib.base import ConfigError
from lib.lambdas.discover import Discover

keywordLocalAccount = 'LOCAL'

def has_expected_attribute(src, id, aname, expected):
    if not (aname in src):
        msg = "Attribute '{}' is missing from record '{}'".format(aname, id)
        logging.warning(msg)
        return False
    actual = src[aname]
    if actual != expected:
        msg = "Attribute '{}' has value '{}'. Expected '{}'. Record Id '{}'".format(aname, actual, expected, id)
        logging.warning(msg)
        return False
    return True

def get_attribute(src, context, aname):
    if not (aname in src):
        msg = "Attribute '{}' is missing from '{}'".format(aname, context)
        logging.warning(msg)
        return None
    return src[aname]


def get_base_config_rule_name(id, qval):
    spos = qval.find("-conformance-pack-")
    if spos <= 0:
        msg = "Qualified config rule name '{}' in record '{}' is not in expected format".format(qval, id)
        logging.warning(msg)
        return None
    return qval[0:spos]

def extract_dispatch(messageId, body):
    if not has_expected_attribute(body, messageId, 'detail-type', "Config Rules Compliance Change"): return None
    if not has_expected_attribute(body, messageId, 'source', "aws.config"): return None

    detail = get_attribute(body, messageId, 'detail')
    if not detail: return None
    resourceId = get_attribute(detail, messageId, "resourceId")
    if not resourceId: return None
    resourceType = get_attribute(detail, messageId, "resourceType")
    if not resourceType: return None
    awsAccountId = get_attribute(detail, messageId, "awsAccountId")
    if not awsAccountId: return None
    awsRegion = get_attribute(detail, messageId, "awsRegion")
    if not awsRegion: return None
    configRuleNameQualified = get_attribute(detail, messageId, "configRuleName")
    if not configRuleNameQualified: return None
    if not has_expected_attribute(detail, messageId, 'messageType', "ComplianceChangeNotification"): return None
    newEvaluationResult = get_attribute(detail, messageId, "newEvaluationResult")
    if not newEvaluationResult: return None
    complianceType = get_attribute(newEvaluationResult, messageId, "complianceType")
    if not complianceType: return None
    configRuleNameBase = get_base_config_rule_name(messageId, configRuleNameQualified)
    if not configRuleNameBase: return None
    return {
        'messageId': messageId,
        'complianceType': complianceType,
        'configRuleNameQualified': configRuleNameQualified,
        'configRuleNameBase': configRuleNameBase,
        'awsAccountId': awsAccountId,
        'awsRegion': awsRegion,
        'resourceType': resourceType,
        'resourceId': resourceId
    }

def create_dispatch(record):
    if not ("messageId" in record):
        logging.warning("Record is missing messageId. Skipping")
        return None
    messageId = record["messageId"]
    bodyjson = get_attribute(record, messageId, 'body')
    if not bodyjson: return None
    body = json.loads(bodyjson)
    dispatch = extract_dispatch(messageId, body)
    if not dispatch: return None

    logging.info("Received Compliance Event: %s", dispatch)
    complianceType = dispatch['complianceType']
    if complianceType == 'NON_COMPLIANT':
        return dispatch
    return None


def createDispatchList(event):
    dispatchList = []
    records = get_attribute(event, "event", 'Records')
    if records:
        for record in records:
            dispatch = create_dispatch(record)
            if dispatch:
                dispatchList.append(dispatch)
    return dispatchList


class Parser:
    def __init__(self, profile :Profile):
        self._profile = profile
        self._discover = Discover(profile)

    def get_account_desc(self, optLandingZone, accountId):
        if not optLandingZone:
            return {
                'Name': keywordLocalAccount,
                'Email': keywordLocalAccount
            }
        targetDesc = self._discover.getAccountDescription(accountId)
        targetStatus = targetDesc['Status']
        if targetStatus != 'ACTIVE':
            logging.info("Skipping account %s with status %s", accountId, targetStatus)
            return None
        return {
            'Name': targetDesc['Name'],
            'Email': targetDesc['Email']
        }

    def get_target_role(self, optLandingZone, accountId):
        targetRole = None
        if optLandingZone:
            targetRole = optLandingZone['RemediationRoleName']
        else:
            if self._profile.accountId == accountId:
                targetRole = keywordLocalAccount
        if not targetRole:
            erm = "Cannot remediate account {} without a remediation role".format(accountId)
            logging.error(erm)
            raise ConfigError(erm)
        return targetRole

    def get_action(self, configRuleName, accountName):
        action = cfgrules.action(configRuleName, accountName)
        if action: return action
        return 'remediate'

    def get_preview(self, configRuleName, accountName):
        preview = cfgrules.isPreview(configRuleName, accountName)
        if preview is None: return True
        return preview

    def get_manual_tag_name(self, configRuleName, accountName):
        tagName = cfgrules.manualRemediationTagName(configRuleName, accountName)
        if tagName: return tagName
        tagName = "DoNotAutoRemediate"
        logging.warning("No manual remediation tag defined for rule %s; will use %s", configRuleName, tagName)
        return tagName

    def get_auto_resource_tags(self, configRuleName, accountName):
        tags = cfgrules.autoResourceTags(configRuleName, accountName)
        if tags: return tags
        tags = {'AutoDeployed': 'True'}
        logging.warning("No tags defined for auto-deployed resources by rule %s; will use %s", configRuleName, tags)
        return tags

    def get_stack_name_pattern(self, configRuleName, accountName):
        pattern = cfgrules.stackNamePattern(configRuleName, accountName)
        if pattern: return pattern
        conformancePackName = cfgrules.conformancePackName()
        pattern = conformancePackName + "-AutoDeploy-{}"
        logging.warning("No stack name pattern defined for auto-deployed stacks by rule %s; will use %s", configRuleName, pattern)
        return pattern

    def create_invoke(self, optLandingZone, dispatch):
        targetAccountId = dispatch['awsAccountId']
        optTargetDesc = self.get_account_desc(optLandingZone, targetAccountId)
        if not optTargetDesc: return None
        targetRole = self.get_target_role(optLandingZone, targetAccountId)
        targetAccountName = optTargetDesc['Name']
        targetAccountEmail = optTargetDesc['Email']
        configRuleName = dispatch['configRuleNameBase']
        ruleCodeFolder = cfgrules.codeFolder(configRuleName, targetAccountName)
        if not ruleCodeFolder:
            logging.info("No auto remediation defined for rule %s and account %s", configRuleName, targetAccountName)
            return None
        functionName = cfginstall.ruleFunctionName(ruleCodeFolder)
        target = {}
        target['awsAccountId'] = targetAccountId
        target['awsAccountName'] = targetAccountName
        target['awsAccountEmail'] = targetAccountEmail
        target['awsRegion'] = dispatch['awsRegion']
        target['roleName'] = targetRole
        target['resourceType'] = dispatch['resourceType']
        target['resourceId'] = dispatch['resourceId']
        event = {}
        event['configRuleName'] = configRuleName
        event['action'] = self.get_action(configRuleName, targetAccountName)
        event['preview'] = self.get_preview(configRuleName, targetAccountName)
        event['conformancePackName'] = cfgrules.conformancePackName()
        event['manualTagName'] = self.get_manual_tag_name(configRuleName, targetAccountName)
        event['autoResourceTags'] = self.get_auto_resource_tags(configRuleName, targetAccountName)
        event['stackNamePattern'] = self.get_stack_name_pattern(configRuleName, targetAccountName)
        event['target'] = target
        return {'functionName': functionName, 'event': event}

    def createInvokeList(self, dispatchList):
        optLandingZone = self._discover.discoverLandingZone()
        invokeList = []
        for dispatch in dispatchList:
            optInvoke = self.create_invoke(optLandingZone, dispatch)
            if not optInvoke: continue
            invoke = {'functionName': optInvoke['functionName'], 'event': optInvoke['event']}
            invokeList.append(invoke)
        return invokeList

import logging
import json
from typing import List

import cfg.core as cfgCore
import cfg.rules as cfgrules

from lib.rdq import Profile
from lib.base import ConfigError
from lib.base.request import DispatchEvent, DispatchEventTarget
from lib.lambdas.discovery import LandingZoneDiscovery

keywordLocalAccount = 'LOCAL'

class RuleInvocation:
    def __init__(self, functionName :str, event :DispatchEvent):
        self._functionName = functionName
        self._event = event

    @property
    def functionName(self) -> str: return self._functionName

    @property
    def event(self) -> DispatchEvent: return self._event

    def toDict(self):
        d = dict()
        d['functionName'] = self._functionName
        d['event'] = self._event.toDict()
        return d

    def __str__(self):
        return json.dumps(self.toDict())


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
        dispatch['action'] = 'remediate'
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
        self._discover = LandingZoneDiscovery(profile)

    def get_account_desc(self, optLandingZone, accountId):
        if not optLandingZone:
            return {
                'Name': keywordLocalAccount,
                'Email': keywordLocalAccount
            }
        targetDesc = self._discover.getAccountDescriptor(accountId)
        if not targetDesc.isActive:
            logging.info("Skipping account %s with status %s", accountId, targetDesc.status)
            return None
        return {
            'Name': targetDesc.accountName,
            'Email': targetDesc.accountEmail
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

    def get_preview(self, configRuleName, action, accountName):
        preview = cfgrules.isPreview(configRuleName, action, accountName)
        if not (preview is None): return preview
        return True

    def get_deployment_method(self, configRuleName, action, accountName):
        dm = cfgrules.deploymentMethod(configRuleName, action, accountName)
        if not (dm is None): return dm
        return {}

    def get_stack_name_pattern(self, configRuleName, action, accountName):
        pattern = cfgrules.stackNamePattern(configRuleName, action, accountName)
        if not (pattern is None): return pattern
        conformancePackName = cfgrules.conformancePackName()
        pattern = conformancePackName + "-AutoDeploy-{}"
        return pattern

    def get_manual_tag_name(self, configRuleName, action, accountName):
        tagName = cfgrules.manualRemediationTagName(configRuleName, action, accountName)
        if not (tagName is None): return tagName
        tagName = "DoNotAutoRemediate"
        logging.warning("No manual remediation tag defined for rule %s; will use %s", configRuleName, tagName)
        return tagName

    def get_auto_resource_tags(self, configRuleName, action, accountName):
        tags = cfgrules.autoResourceTags(configRuleName, action, accountName)
        if not (tags is None): return tags
        tags = {'AutoDeployed': 'True'}
        logging.warning("No tags defined for auto-deployed resources by rule %s; will use %s", configRuleName, tags)
        return tags


    def create_invoke(self, optLandingZone, dispatch):
        action = dispatch['action']
        targetAccountId = dispatch['awsAccountId']
        optTargetDesc = self.get_account_desc(optLandingZone, targetAccountId)
        if not optTargetDesc: return None
        targetRole = self.get_target_role(optLandingZone, targetAccountId)
        targetAccountName = optTargetDesc['Name']
        targetAccountEmail = optTargetDesc['Email']
        configRuleName = dispatch['configRuleNameBase']
        ruleCodeFolder = cfgrules.codeFolder(configRuleName, action, targetAccountName)
        if not ruleCodeFolder:
            logging.info("No %s implementation defined for rule %s and account %s", action, configRuleName, targetAccountName)
            return None
        functionName = cfgCore.ruleFunctionName(ruleCodeFolder)
        det = {}
        det['awsAccountId'] = targetAccountId
        det['awsAccountName'] = targetAccountName
        det['awsAccountEmail'] = targetAccountEmail
        det['awsRegion'] = dispatch['awsRegion']
        det['roleName'] = targetRole
        det['resourceType'] = dispatch['resourceType']
        det['resourceId'] = dispatch['resourceId']
        target = DispatchEventTarget(det)
        de = {}
        de['configRuleName'] = configRuleName
        de['action'] = action
        de['conformancePackName'] = cfgrules.conformancePackName()
        de['preview'] = self.get_preview(configRuleName, action, targetAccountName)
        de['deploymentMethod'] = self.get_deployment_method(configRuleName, action, targetAccountName)
        de['manualTagName'] = self.get_manual_tag_name(configRuleName, action, targetAccountName)
        de['autoResourceTags'] = self.get_auto_resource_tags(configRuleName, action, targetAccountName)
        de['stackNamePattern'] = self.get_stack_name_pattern(configRuleName, action, targetAccountName)
        event = DispatchEvent(de, target)
        return {'functionName': functionName, 'event': event}

    def createInvokeList(self, dispatchList) -> List[RuleInvocation]:
        optLandingZone = self._discover.discoverLandingZone()
        invokeList = []
        for dispatch in dispatchList:
            optInvoke = self.create_invoke(optLandingZone, dispatch)
            if not optInvoke: continue
            invoke = RuleInvocation(optInvoke['functionName'], optInvoke['event'])
            invokeList.append(invoke)
        return invokeList

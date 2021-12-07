import logging
import json

import cfg.installer as cfginstall
import cfg.rules as cfgrules

from lib.base import ConfigError
import lib.lambdas.discover as discover

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

def createInvokeList(profile, dispatchList):
    conformancePackName = cfgrules.conformancePackName()
    optLandingZone = discover.discoverLandingZone(profile)
    functionCallList = []
    for dispatch in dispatchList:
        targetAccountId = dispatch['awsAccountId']
        configRuleMap = cfgrules.configRuleMapping(targetAccountId)
        previewRuleList = cfgrules.previewRuleList(targetAccountId)
        previewInclusive = cfgrules.isPreviewRuleListInclusive(targetAccountId)
        previewRuleSet = set(previewRuleList)
        configRuleName = dispatch['configRuleNameBase']
        ruleCodeFolder = None
        if configRuleName in configRuleMap:
            ruleCodeFolder = configRuleMap[configRuleName]
        if not ruleCodeFolder:
            logging.info("No auto remediation defined for rule %s", configRuleName)
            continue
        functionName = cfginstall.ruleFunctionName(ruleCodeFolder)
        isPreviewSetMember = configRuleName in previewRuleSet
        isPreview = isPreviewSetMember if previewInclusive else (not isPreviewSetMember)
        isLocalAccount = profile.accountId == targetAccountId
        targetRole = None
        if optLandingZone:
            targetRole = optLandingZone['RemediationRoleName']
        else:
            if isLocalAccount:
                targetRole = 'LOCAL'
        if not targetRole:
            erm = "Cannot remediate account {} without a remediation role".format(targetAccountId)
            logging.error(erm)
            raise ConfigError(erm)
        manualTagName = cfgrules.manualRemediationTagName(configRuleName, targetAccountId)
        if not manualTagName:
            manualTagName = "DoNotAutoRemediate"
            logging.warning("No manual remediation tag defined for rule %s; will use %s", configRuleName, manualTagName)
        autoResourceTags = cfgrules.autoResourceTags(configRuleName, targetAccountId)
        if not autoResourceTags:
            autoResourceTags = {'AutoDeployed': 'True'}
            logging.warning("No tags defined for auto-deployed resources by rule %s; will use %s", configRuleName, autoResourceTags)
        stackNamePattern = cfgrules.stackNamePattern(configRuleName, targetAccountId)
        if not stackNamePattern:
            stackNamePattern = conformancePackName + "-AutoDeploy-{}"
            logging.warning("No stack name pattern defined for auto-deployed stacks by rule %s; will use %s", configRuleName, stackNamePattern)

        awsRegion = dispatch['awsRegion']
        resourceType = dispatch['resourceType']
        resourceId = dispatch['resourceId']
        eventMap = {
            'preview': isPreview,
            'conformancePackName': conformancePackName,
            'configRuleName': configRuleName,
            'manualTagName': manualTagName,
            'autoResourceTags': autoResourceTags,
            'stackNamePattern': stackNamePattern,
            'target': {
                'awsAccountId': targetAccountId,
                'awsRegion': awsRegion,
                'roleName': targetRole,
                'resourceType': resourceType,
                'resourceId': resourceId
            }
        }
        functionCallList.append({'functionName': functionName, 'event': eventMap})
    return functionCallList

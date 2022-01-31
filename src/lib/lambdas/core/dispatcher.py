import os, logging, json, time
from typing import List

import cfg.core as cfgCore
import cfg.roles as cfgRoles

from lib.base import ConfigError, RK
import lib.base.ruleresponse as rr

from lib.rdq import Profile
from lib.rdq.svclambda import LambdaClient
from lib.rdq.svccwm import CwmClient

from lib.lambdas.core.parser import Parser, RuleInvocation
import lib.lambdas.core.ruleselector as ruleselector
import lib.lambdas.core.cwdims as cwdims


def _get_remediation_role():
    envName = cfgCore.environmentVariableNameRemediationRole()
    roleName = os.environ.get(envName)
    if roleName: return roleName
    msg = "Required environment variable `{}` is undefined".format(envName)
    raise ConfigError(msg)

def _is_standalone_mode(roleName):
    standaloneRoles = cfgRoles.standaloneRoles()
    if not standaloneRoles: return False
    optStandaloneRemediation = standaloneRoles.get('Remediation')
    if not optStandaloneRemediation: return False
    return roleName == optStandaloneRemediation

def _has_expected_attribute(src, id, aname, expected):
    if not (aname in src):
        report = {
            RK.Synopsis: 'SkippedRecord',
            RK.Cause: 'Required attribute missing from record',
            'AttributeName': aname,
            'RecordId': id
        }
        logging.warning(report)
        return False
    actual = src[aname]
    if actual != expected:
        report = {
            RK.Synopsis: 'SkippedRecord',
            RK.Cause: 'Attribute has an unexpected value',
            'AttributeName': aname,
            'ActualValue': actual,
            'ExpectedValue': expected,
            'RecordId': id
        }
        logging.warning(report)
        return False
    return True

def _get_attribute(src, context, aname):
    if not (aname in src):
        report = {
            RK.Synopsis: 'SkippedRecord',
            RK.Cause: 'Required attribute is missing',
            'AttributeName': aname,
            'Context': context,
            'RecordId': id
        }
        logging.warning(report)
        return None
    return src[aname]


class RuleOutcome:
    def __init__(self, retry :bool, success :bool = False):
        self.retry = retry
        self.success = success

class Dispatcher:
    def __init__(self, profile :Profile, retrySleepSecs=2):
        self._profile = profile
        self._cwmclient = CwmClient(profile)
        self._lambdaclient = LambdaClient(profile)
        remediationRoleName = _get_remediation_role()
        isStandaloneMode = _is_standalone_mode(remediationRoleName)
        self._parser = Parser(profile, remediationRoleName, isStandaloneMode)
        self._retrySleepSecs = retrySleepSecs

    def get_base_config_rule_name(self, id, qval):
        optBaseName = ruleselector.getRuleBaseName(qval)
        if optBaseName: return optBaseName
        cause = "Qualified config rule name '{}' in record '{}' is not in expected format".format(qval, id)
        report = {RK.Synopsis: 'SkippedMessage', RK.Cause: cause}
        logging.warning(report)

    def extract_dispatch(self, messageId, body):
        if not _has_expected_attribute(body, messageId, 'detail-type', "Config Rules Compliance Change"): return None
        if not _has_expected_attribute(body, messageId, 'source', "aws.config"): return None

        detail = _get_attribute(body, messageId, 'detail')
        if not detail: return None
        resourceId = _get_attribute(detail, messageId, "resourceId")
        if not resourceId: return None
        resourceType = _get_attribute(detail, messageId, "resourceType")
        if not resourceType: return None
        awsAccountId = _get_attribute(detail, messageId, "awsAccountId")
        if not awsAccountId: return None
        awsRegion = _get_attribute(detail, messageId, "awsRegion")
        if not awsRegion: return None
        configRuleNameQualified = _get_attribute(detail, messageId, "configRuleName")
        if not configRuleNameQualified: return None
        if not _has_expected_attribute(detail, messageId, 'messageType', "ComplianceChangeNotification"): return None
        newEvaluationResult = _get_attribute(detail, messageId, "newEvaluationResult")
        if not newEvaluationResult: return None
        complianceType = _get_attribute(newEvaluationResult, messageId, "complianceType")
        if not complianceType: return None
        configRuleNameBase = self.get_base_config_rule_name(messageId, configRuleNameQualified)
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

    def create_dispatch(self, record):
        if not ("messageId" in record):
            report = {RK.Synopsis: 'SkippedMessage', RK.Cause: 'Missing messageId', 'Record': record}
            logging.warning(report)
            return None
        messageId = record["messageId"]
        bodyjson = _get_attribute(record, messageId, 'body')
        if not bodyjson: return None
        body = json.loads(bodyjson)
        dispatch = self.extract_dispatch(messageId, body)
        if not dispatch: return None

        report = {RK.Synopsis: 'ReceivedComplianceEvent', 'ParsedEvent': dispatch}
        logging.info(report)
        complianceType = dispatch['complianceType']
        if complianceType == 'NON_COMPLIANT':
            dispatch['action'] = 'remediate'
            return dispatch
        return None

    def create_dispatch_list(self, event):
        dispatchList = []
        records = _get_attribute(event, "event", 'Records')
        if records:
            for record in records:
                dispatch = self.create_dispatch(record)
                if dispatch:
                    dispatchList.append(dispatch)
        return dispatchList

    def publish_cloudwatch_metrics(self, ri :RuleInvocation, ar :rr.ActionResponse):
        action = ar.action
        cwNamespace = cfgCore.coreCloudWatchNamespace(action)
        cwMetric = "{}.{}".format(ar.major, ar.minor)
        dimensionMaps = cwdims.getDimensionMaps(ri.event)
        for dimensionMap in dimensionMaps:
            self._cwmclient.putCount(cwNamespace, cwMetric, dimensionMap)

    def publish_preview(self, ri :RuleInvocation, ar :rr.ActionResponse):
        if not ri.event.preview: return
        syn = "Function {} Preview".format(ri.functionName)
        report = {RK.Synopsis: syn, 'Preview': ar.preview}
        logging.warning(report)

    def analyze_response(self, ri :RuleInvocation, fr :dict) -> RuleOutcome:
        functionName = ri.functionName
        attempt = ri.attempt
        event = ri.event
        statusCode = fr['StatusCode']
        payload = fr['Payload']
        if statusCode != 200:
            report = {
                RK.Synopsis: "BadLambdaFunctionStatusCode",
                'StatusCode': statusCode,
                'Function': functionName,
                'Attempt': attempt,
                'Response': fr,
                'Event': event.toDict()
            }
            logging.error(report)
            return RuleOutcome(True)

        ar = rr.ActionResponse(source=payload)
        self.publish_cloudwatch_metrics(ri, ar)

        if ar.isTimeout:
            report = {
                RK.Synopsis: "LambdaFunctionTimeout",
                'Function': functionName,
                'Attempt': attempt,
                'Event': event.toDict()
            }
            logging.error(report)
            return RuleOutcome(True)

        self.publish_preview(ri, ar)

        if ar.isSuccess:
            report = {
                RK.Synopsis: "LambdaFunctionSuccess",
                'Function': functionName,
                'Attempt': attempt,
                'Response': ar.toDict(),
                'Event': event.toDict()
            }
            logging.info(report)
            return RuleOutcome(False, True)
        
        report = {
            RK.Synopsis: "LambdaFunctionFailed",
            'Function': functionName,
            'Attempt': attempt,
            'Response': ar.toDict(),
            'Event': event.toDict()
        }
        logging.error(report)
        return RuleOutcome(False, False)


    def dispatch_rule_invocations(self, ruleInvocations :List[RuleInvocation]):
        retryList = []
        for ri in ruleInvocations:
            eventDict = ri.event.toDict()
            functionResponse = self._lambdaclient.invokeFunctionJson(ri.functionName, eventDict)
            ruleOutcome = self.analyze_response(ri, functionResponse)
            if ruleOutcome.retry:
                retryList.append(ri.newInvocation())
        return retryList

    def dispatch(self, event :dict):
        dispatchList = self.create_dispatch_list(event)
        if len(dispatchList) == 0: return
        ruleInvocations = self._parser.createInvokeList(dispatchList)
        while True:
            if len(ruleInvocations) == 0: return
            retryList = self.dispatch_rule_invocations(ruleInvocations)
            if len(ruleInvocations) == 1 and len(retryList) == 1:
                time.sleep(self._retrySleepSecs)
            ruleInvocations = retryList

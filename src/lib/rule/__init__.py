import logging
import json
import time

from lib.base import initLogging, Tags
from lib.rdq import Profile, RdqError, RdqTimeout


class RuleImplementationError(Exception):
    def __init__(self, message):
        self._message = message

    def __str__(self):
        return self._message
    
    @property
    def message(self):
        return self._message

class RuleTimeoutError(Exception):
    def __init__(self, message, task=None):
        if task:
            secs = int(task.elapsedSecs)
            m = "{}; elapsed {} secs".format(message, secs)
        else:
            m = message
        self._message = m

    def __str__(self):
        return self._message
    
    @property
    def message(self):
        return self._message


def _required(argVal, argName):
    if argVal: return argVal
    erm = "Require a value for {}".format(argName)

def _required_value(src, propName):
    if propName in src: return src[propName]
    erm = "Missing value for required property {}".format(propName)
    raise RuleImplementationError(erm)

def _defaulted_value(src, propName, defValue):
    if propName in src: return src[propName]
    return defValue

class Task:
    def __init__(self, props):
        self._props = props
        self._autoResourceTags = Tags(props['autoResourceTags'], 'autoResourceTags')
        self._startedAt = time.time()
    
    @property
    def action(self): return self._props['action']

    @property
    def isActionRemediate(self): return self._props['action'] == 'remediate'

    @property
    def isPreview(self): return self._props['isPreview']

    @property
    def accountId(self): return self._props['accountId']

    @property
    def accountName(self): return self._props['accountName']

    @property
    def accountEmail(self): return self._props['accountEmail']

    @property
    def regionName(self): return self._props['regionName']

    @property
    def resourceType(self): return self._props['resourceType']

    @property
    def resourceId(self): return self._props['resourceId']

    @property
    def conformancePackName(self): return self._props['conformancePackName']

    @property
    def manualTagName(self): return self._props['manualTagName']

    @property
    def autoResourceTags(self) -> dict: return self._autoResourceTags

    @property
    def stackNamePattern(self): return self._props['stackNamePattern']

    @property
    def deploymentMethod(self) -> dict: return self._props['deploymentMethod']

    @property
    def elapsedSecs(self):
        return time.time() - self._startedAt

    def __str__(self):
        return json.dumps(self._props)
    

class RuleMain:
    def __init__(self, logLevelVariable='LOGLEVEL', defaultLevel='INFO'):
        initLogging(logLevelVariable, defaultLevel)
        self._handlers = []
    
    def _select_handling_method(self, configRuleName, resourceType):
        for handler in self._handlers:
            if handler['configRuleName'] != configRuleName: continue
            if handler['resourceType'] != resourceType: continue
            return handler['handlingMethod']
        erm = "No handling method defined for {} and {}".format(configRuleName, resourceType)
        raise RuleImplementationError(erm)

    def _session_name(self, configRuleName):
        out = 'remediate-' + configRuleName
        return out[0:64]

    def _remediate_imp(self, event):
        configRuleName = _required_value(event, 'configRuleName')
        action = _defaulted_value(event, 'action', 'remediate')
        isPreview = _defaulted_value(event, 'preview', True)
        target = _required_value(event, 'target')
        resourceType = _required_value(target, 'resourceType')
        resourceId = _required_value(target, 'resourceId')
        handlingMethod = self._select_handling_method(configRuleName, resourceType)
        awsAccountId = _required_value(target, 'awsAccountId')
        awsAccountName = _required_value(target, 'awsAccountName')
        awsAccountEmail = _required_value(target, 'awsAccountEmail')
        awsRegion = _required_value(target, 'awsRegion')
        roleName = _required_value(target, 'roleName')
        taskProps = {
            'configRuleName': configRuleName,
            'action': action,
            'isPreview': isPreview,
            'resourceType': resourceType,
            'resourceId': resourceId,
            'accountId': awsAccountId,
            'accountName': awsAccountName,
            'accountEmail': awsAccountEmail,
            'regionName': awsRegion,
            'conformancePackName': _required_value(event, 'conformancePackName'),
            'manualTagName': _required_value(event, 'manualTagName'),
            'autoResourceTags': _required_value(event, 'autoResourceTags'),
            'stackNamePattern': _required_value(event, 'stackNamePattern'),
            'deploymentMethod': _defaulted_value(event, 'deploymentMethod', {})
        }
        task = Task(taskProps)
        sessionName = self._session_name(configRuleName)
        try:
            fromProfile = Profile(regionName=awsRegion)
            if roleName == 'LOCAL':
                targetProfile = fromProfile
            else:
                targetProfile = fromProfile.assumeRole(awsAccountId, roleName, awsRegion, sessionName)
            targetProfile.enablePreview(isPreview)
            previewResponse = {}
            remediationResponse = handlingMethod(targetProfile, task)
            if targetProfile.isPreviewing:
                previewResponse = targetProfile.enablePreview(False)
            return {
                'isPreview': isPreview,
                'previewResponse': previewResponse,
                'remediationResponse': remediationResponse
            }
        except RuleTimeoutError as e:
            logging.warning("Timeout in remediation handler. | Cause: %s | Task: %s", e.message, task)
            return {
                'remediationTimeout': e.message
            }
        except RdqTimeout as e:
            logging.warning("RdqTimeout in remediation handler. | Cause: %s | Task: %s", e.message, task)
            return {
                'remediationTimeout': e.message
            }
        except RdqError as e:
            ectx = {
                "configRuleName": configRuleName,
                "resourceType": resourceType,
                "resourceId": resourceId,
                "targetAccountId": awsAccountId,
                "roleName": roleName
            }
            logging.error("RdqError in remediation handler. | Cause: %s | Context: %s", e.message, ectx)
            return {
                'remediationFailure': e.message
            }

    def addHandler(self, configRuleName, resourceType, handlingMethod):
        handler = {
            'configRuleName': _required(configRuleName, 'configRuleName'),
            'resourceType': _required(resourceType, 'resourceType'),
            'handlingMethod': _required(handlingMethod, 'handlingMethod')
        }
        self._handlers.append(handler)
    
    def remediate(self, event):
        try:
            return self._remediate_imp(event)
        except RuleImplementationError as e:
            logging.error("RuleImplementationError in remediation main. | Cause: %s | Event: %s", e.message, event)
            return {
                'remediationFailure': e.message
            }

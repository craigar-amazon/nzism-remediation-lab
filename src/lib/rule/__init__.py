import logging
import json
import time

from typing import Callable

from lib.base import initLogging, Tags
import lib.base.ruleresponse as rr
from lib.rdq import Profile, RdqError, RdqTimeout


class RuleSoftwareError(Exception):
    def __init__(self, message):
        self._message = message

    def __str__(self):
        return self._message
    
    @property
    def message(self):
        return self._message

class RuleConfigurationError(Exception):
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
    raise RuleSoftwareError(erm)

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
    def autoResourceTags(self) -> Tags: return self._autoResourceTags

    @property
    def stackNamePattern(self): return self._props['stackNamePattern']

    @property
    def deploymentMethod(self) -> dict: return self._props['deploymentMethod']

    @property
    def configRuleName(self): return self._props['configRuleName']

    @property
    def roleName(self): return self._props['roleName']

    @property
    def elapsedSecs(self):
        return time.time() - self._startedAt

    def __str__(self):
        return json.dumps(self._props)
    

class RuleMain:
    def __init__(self, logLevelVariable='LOGLEVEL', defaultLevel='INFO'):
        initLogging(logLevelVariable, defaultLevel)
        self._remediationHandlers = []
        self._baselineHandlers = []

    def _create_handler(self, configRuleName, resourceType, handlingMethod):
        return {
            'configRuleName': _required(configRuleName, 'configRuleName'),
            'resourceType': _required(resourceType, 'resourceType'),
            'handlingMethod': _required(handlingMethod, 'handlingMethod')
        }

    def _select_handling_table(self, action):
        if action == 'remediate': return self._remediationHandlers    
        if action == 'baseline': return self._baselineHandlers
        erm = "Unsupported handler table type `{}`".format(action)
        raise RuleSoftwareError(erm)

    def _select_handling_method(self, configRuleName, action, resourceType):
        handlingTable = self._select_handling_table(action)
        for handler in handlingTable:
            if handler['configRuleName'] != configRuleName: continue
            if handler['resourceType'] != resourceType: continue
            return handler['handlingMethod']
        erm = "No handling method defined for rule `{}`, type `{}`, and action `{}`".format(configRuleName, resourceType, action)
        raise RuleConfigurationError(erm)

    def _required_action(self, target):
        actionSet= set(['remediate','baseline'])
        action = _defaulted_value(target, 'action', 'remediate')
        if action in actionSet: return action
        erm = "Unsupported action `{}`".format(action)
        raise RuleSoftwareError(erm)
    
    def _required_resourceId(self, target, action):
        if action == 'baseline': return '*'
        return _required_value(target, 'resourceId')

    def _session_name(self, action, configRuleName):
        out = "{}-{}".format(action, configRuleName)
        return out[0:64]

    def _action_task(self, handlingMethod :Callable[[Profile, Task], rr.ActionResponse], task :Task) -> rr.ActionResponse:
        try:
            action = task.action
            awsAccountId = task.accountId
            awsRegion = task.regionName
            configRuleName = task.configRuleName
            isPreview = task.isPreview
            roleName = task.roleName
            sessionName = self._session_name(action, configRuleName)
            fromProfile = Profile(regionName=awsRegion)
            if roleName == 'LOCAL':
                targetProfile = fromProfile
            else:
                targetProfile = fromProfile.assumeRole(awsAccountId, roleName, awsRegion, sessionName)
            targetProfile.enablePreview(isPreview)
            previewResponse = {}
            actionResponse = handlingMethod(targetProfile, task)
            if targetProfile.isPreviewing:
                previewResponse = targetProfile.enablePreview(False)
                actionResponse.putPreview(previewResponse)
            return actionResponse
        except RuleTimeoutError as e:
            logging.warning("Timeout in %s handler. | Cause: %s | Task: %s", action, e.message, task)
            return rr.ActionTimeoutConfiguration(action, e.message)
        except RdqTimeout as e:
            logging.warning("RdqTimeout in %s handler. | Cause: %s | Task: %s", action, e.message, task)
            return rr.ActionTimeoutRdq(action, e.message)
        except RdqError as e:
            logging.error("RdqError in %s handler. | Cause: %s | Task: %s", action, e.message, task)
            return rr.ActionFailureRdq(action, e.message)
        except RuleConfigurationError as e:
            logging.error("RuleConfigurationError in %s handler. | Cause: %s | Task: %s", action, e.message, task)
            return rr.ActionFailureConfiguration(action, e.message)
        except RuleSoftwareError as e:
            logging.error("RuleSoftwareError in %s handler. | Cause: %s | Task: %s", action, e.message, task)
            return rr.ActionFailureSoftware(action, e.message)
        except Exception as e:
            syn = "{} error in {} handler".format(type(e), action)
            logging.exception("%s | Cause: %s | Task: %s", syn, e, task)
            return rr.ActionFailure(action, syn)

    def _action_event(self, event) -> rr.ActionResponse:
        action = 'setup'
        try:
            action = self._required_action(event)
            configRuleName = _required_value(event, 'configRuleName')
            isPreview = _defaulted_value(event, 'preview', True)
            target = _required_value(event, 'target')
            resourceType = _required_value(target, 'resourceType')
            handlingMethod = self._select_handling_method(configRuleName, action, resourceType)
            resourceId = self._required_resourceId(target, action)
            awsAccountId = _required_value(target, 'awsAccountId')
            awsAccountName = _required_value(target, 'awsAccountName')
            awsAccountEmail = _required_value(target, 'awsAccountEmail')
            awsRegion = _required_value(target, 'awsRegion')
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
                'roleName': _required_value(target, 'roleName'),
                'conformancePackName': _required_value(event, 'conformancePackName'),
                'manualTagName': _required_value(event, 'manualTagName'),
                'autoResourceTags': _required_value(event, 'autoResourceTags'),
                'stackNamePattern': _required_value(event, 'stackNamePattern'),
                'deploymentMethod': _defaulted_value(event, 'deploymentMethod', {})
            }
            task = Task(taskProps)
            return self._action_task(handlingMethod, task)
        except RuleConfigurationError as e:
            logging.error("RuleConfigurationError in task setup | Cause: %s | Event: %s", e.message, event)
            return rr.ActionFailureConfiguration(action, e.message)
        except RuleSoftwareError as e:
            logging.error("RuleSoftwareError in in task setup | Cause: %s | Event: %s", e.message, event)
            return rr.ActionFailureSoftware(action, e.message)
        except Exception as e:
            syn = "{} error in {} handler".format(type(e), action)
            logging.exception("%s | Cause: %s | Task: %s", syn, e, task)
            return rr.ActionFailure(action, syn)

    def addRemediationHandler(self, configRuleName :str, resourceType :str, handlingMethod :Callable[[Profile, Task], rr.RemediationResponse]):
        handler = self._create_handler(configRuleName, resourceType, handlingMethod)
        self._remediationHandlers.append(handler)

    def addBaselineHandler(self, configRuleName :str, resourceType :str, handlingMethod :Callable[[Profile, Task], rr.BaselineResponse]):
        handler = self._create_handler(configRuleName, resourceType, handlingMethod)
        self._baselineHandlers.append(handler)

    def action(self, event):
        actionResponse = self._action_event(event)
        return actionResponse.toDict()

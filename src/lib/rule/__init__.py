import logging
from lib.rdq import Profile, RdqError

def _logerr(msg):
    logging.error(msg)

class RuleImplementationError(Exception):
    def __init__(self, message):
        self._message = message

    def __str__(self):
        return self._message
    
    @property
    def message(self):
        return self._message

def _required(argVal, argName):
    if argVal: return argVal
    erm = "Require a value for {}".format(argName)

def _required_value(src, propName, defValue=None):
    if propName in src: return src[propName]
    if defValue: return defValue
    erm = "Missing value for required property {}".format(propName)
    raise RuleImplementationError(erm)

class RuleMain:
    def __init__(self):
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
        conformancePackName = _required_value(event, 'conformancePackName')
        configRuleName = _required_value(event, 'configRuleName')
        isPreview = _required_value(event, 'preview', True)
        target = _required_value(event, 'target')
        resourceType = _required_value(target, 'resourceType')
        resourceId = _required_value(target, 'resourceId')
        handlingMethod = self._select_handling_method(configRuleName, resourceType)
        awsAccountId = _required_value(target, 'awsAccountId')
        awsRegion = _required_value(target, 'awsRegion')
        roleName = _required_value(target, 'roleName')
        sessionName = self._session_name(configRuleName)
        try:
            fromProfile = Profile(regionName=awsRegion)
            targetProfile = fromProfile.assumeRole(awsAccountId, roleName, awsRegion, sessionName)
            targetProfile.enablePreview(isPreview)
            context = {
                'conformancePackName': conformancePackName
            }
            previewResponse = {}
            remediationResponse = handlingMethod(targetProfile, resourceId, context)
            if targetProfile.isPreviewing:
                previewResponse = targetProfile.enablePreview(False)
            return {
                'isPreview': isPreview,
                'previewResponse': previewResponse,
                'remediationResponse': remediationResponse
            }
        except RdqError as e:
            _logerr("Remedition handler for rule {} and type {} failed".format(configRuleName, resourceType))
            _logerr("ResourceId: {}".format(resourceId))
            _logerr("TargetAccountId: {}".format(awsAccountId))
            _logerr("RoleName: {}".format(roleName))
            _logerr(e)
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
            _logerr("Remedition {} failed".format(self._remediationName))
            _logerr(e)
            return {
                'remediationFailure': e.message
            }

import json

class ActionResponse:
    def __init__(self, **kwargs):
        self._props = {}
        for kw in kwargs.keys():
            if kw == 'source':
                src = kwargs[kw]
                self._props.update(src)
            else:
                self._props[kw] = kwargs[kw]

    def putPreview(self, preview: dict):
        self._props['preview'] = preview

    def action(self) -> str:
        return self._props.get('action', 'general')

    def major(self) -> str:
        return self._props.get('major', 'Failure')

    def minor(self) -> str:
        return self._props.get('minor', 'Software')

    def message(self) -> str:
        return self._props.get('message', 'Unspecified')

    def preview(self) -> dict:
        return self._props.get('preview', {})

    def isSuccess(self) -> bool:
        return self.major() == 'Success'

    def isFailure(self) -> bool:
        return self.major() == 'Failure'

    def isTimeout(self) -> bool:
        return self.major() == 'Timeout'

    def toDict(self) -> dict:
        result = dict(self._props)
        return result

    def __str__(self):
        return json.dumps(self._props)

class RemediationResponse(ActionResponse): pass

class RemediationApplied(RemediationResponse):
    def __init__(self, message):
        ActionResponse.__init__(self, action='remediate', major='Success', minor='Applied', message=message)

class RemediationValidated(RemediationResponse):
    def __init__(self, message):
        ActionResponse.__init__(self, action='remediate', major='Success', minor='Validated', message=message)

class RemediationExemptManual(RemediationResponse):
    def __init__(self):
        ActionResponse.__init__(self, action='remediate', major='Success', minor='ExemptManual', message="Resource tagged for manual remediation")

class BaselineResponse(ActionResponse): pass

class BaselineConfirmed(BaselineResponse):
    def __init__(self, message):
        ActionResponse.__init__(self, action='baseline', major='Success', minor='Confirmed', message=message)

class BaselineExemptManual(BaselineResponse):
    def __init__(self, message):
        ActionResponse.__init__(self, action='baseline', major='Success', minor='ExemptManual', message=message)

class ActionTimeoutConfiguration(ActionResponse):
    def __init__(self, action, message):
        ActionResponse.__init__(self, action=action, major='Timeout', minor='Configuration', message=message)

class ActionTimeoutRdq(ActionResponse):
    def __init__(self, action, message):
        ActionResponse.__init__(self, action=action, major='Timeout', minor='RdqApi', message=message)

class ActionFailureConfiguration(ActionResponse):
    def __init__(self, action, message):
        ActionResponse.__init__(self, action=action, major='Failure', minor='Configuration', message=message)

class ActionFailureRdq(ActionResponse):
    def __init__(self, action, message):
        ActionResponse.__init__(self, action=action, major='Failure', minor='RdqApi', message=message)

class ActionFailureSoftware(ActionResponse):
    def __init__(self, action, message):
        ActionResponse.__init__(self, action=action, major='Failure', minor='Software', message=message)

class ActionFailure(ActionResponse):
    def __init__(self, action, message):
        ActionResponse.__init__(self, action=action, major='Failure', minor='General', message=message)

import json

class DispatchEventTarget:
    def __init__(self, props :dict):
        self._props = props

    @property
    def accountId(self) -> str: return self._props['awsAccountId']

    @property
    def accountName(self) -> str: return self._props['awsAccountName']

    @property
    def accountEmail(self) -> str: return self._props['awsAccountEmail']

    @property
    def regionName(self) -> str: return self._props['awsRegion']

    @property
    def roleName(self) -> str: return self._props['roleName']

    @property
    def resourceType(self) -> str: return self._props['resourceType']

    @property
    def resourceId(self) -> str: return self._props['resourceId']

    def toDict(self):
        return dict(self._props)

    def __str__(self):
        return json.dumps(self._props)


class DispatchEvent:
    def __init__(self, props: dict, target: DispatchEventTarget):
        self._props = props
        self._target = target

    @property
    def configRuleName(self) -> str: return self._props['configRuleName']

    @property
    def action(self) -> str: return self._props['action']

    @property
    def conformancePackName(self) -> str: return self._props['conformancePackName']

    @property
    def preview(self) -> bool: return self._props['preview']

    @property
    def deploymentMethod(self) -> dict: return self._props['deploymentMethod']

    @property
    def manualTagName(self) -> str: return self._props['manualTagName']

    @property
    def autoResourceTags(self) -> dict: return self._props['autoResourceTags']

    @property
    def stackNamePattern(self) -> str: return self._props['stackNamePattern']

    @property
    def target(self) -> DispatchEventTarget: return self._target

    def toDict(self):
        d = dict(self._props)
        d['target'] = self._target.toDict()
        return d

    def __str__(self):
        return json.dumps(self.toDict())
    
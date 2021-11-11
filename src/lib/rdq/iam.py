import botocore

from .base import _is_resource_not_found
from .base import _fail

class IamClient:
    def __init__(self, profile):
        service = 'iam'
        self._profile = profile
        self._service = service
        self._client = profile.getClient(service)

    def get_role(self, roleName):
        try:
            response = self._client.get_role(
                RoleName=roleName
            )
            return response['Role']
        except botocore.exceptions.ClientError as e:
            if _is_resource_not_found(e): return None
            erm = _fail(e, self._service, 'get_role', 'Role', roleName)
            raise Exception(erm)

    def getRole(self, roleName):
        return self.get_role(roleName)

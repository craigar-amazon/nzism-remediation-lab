import botocore
from lib.rdq import RdqError
from lib.rdq.base import ServiceUtils


class OrganizationClient:
    def __init__(self, profile):
        service = 'organizations'
        self._profile = profile
        self._client = profile.getClient(service)
        self._utils = ServiceUtils(profile, service)

    def diagnosticDelegated(self, op):
        accountId = self._profile.accountId
        msg = "Ensure account is delegated administrator"
        self._utils.warning(op, "Account", accountId, msg)


    def describe_organization(self):
        op = 'describe_organization'
        try:
            response = self._client.describe_organization()
            return response['Organization']
        except botocore.exceptions.ClientError as e:
            self.diagnosticDelegated(op)
            raise RdqError(self._utils.fail(e, op))

    def getOrganizationId(self):
        org = self.describe_organization()
        return org['Id']
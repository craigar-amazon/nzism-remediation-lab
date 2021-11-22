import botocore
from lib.rdq import RdqError
from .base import ServiceUtils


class OrganizationClient:
    def __init__(self, profile):
        service = 'organizations'
        self._profile = profile
        self._client = profile.getClient(service)
        self._utils = ServiceUtils(profile, service)

    def diagnosticDelegated(self, op):
        accountId = self._profile.accountId
        msg = "Ensure account {} is delegated administrator".format(accountId)
        self._utils.diagnostic(op, msg)


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
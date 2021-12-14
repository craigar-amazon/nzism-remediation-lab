import json
import botocore
from lib.rdq import RdqError
from lib.rdq.base import ServiceUtils

class AccountDescriptor:
    def __init__(self, props):
        self._props = props

    @property
    def accountId(self):
        return self._props['Id']

    @property
    def arn(self):
        return self._props['Arn']

    @property
    def accountName(self):
        return self._props['Name']

    @property
    def accountEmail(self):
        return self._props['Email']

    @property
    def status(self):
        return self._props['Status']

    @property
    def isActive(self):
        return self._props['Status'] == 'ACTIVE'

    def toDict(self) -> dict:
        return self._props

    def __str__(self):
        return json.dumps(self._props)


class OrganizationDescriptor:
    def __init__(self, props):
        self._props = props

    @property
    def id(self):
        return self._props['Id']

    @property
    def arn(self):
        return self._props['Arn']

    @property
    def masterAccountId(self):
        return self._props['MasterAccountId']

    @property
    def masterAccountEmail(self):
        return self._props['MasterAccountEmail']

    def toDict(self) -> dict:
        return self._props

    def __str__(self):
        return json.dumps(self._props)


class OrganizationClient:
    def __init__(self, profile):
        service = 'organizations'
        self._profile = profile
        self._client = profile.getClient(service)
        self._utils = ServiceUtils(profile, service)

    def diagnosticDelegated(self, op):
        accountId = self._profile.accountId
        msg = "Ensure account is delegated administrator for Organization"
        self._utils.warning(op, "Account", accountId, msg)


    def describe_organization(self):
        op = 'describe_organization'
        try:
            response = self._client.describe_organization()
            return response['Organization']
        except botocore.exceptions.ClientError as e:
            self.diagnosticDelegated(op)
            raise RdqError(self._utils.fail(e, op))

    def describe_account(self, accountId):
        op = 'describe_account'
        try:
            response = self._client.describe_account(
                AccountId = accountId
            )
            return response['Account']
        except botocore.exceptions.ClientError as e:
            self.diagnosticDelegated(op)
            raise RdqError(self._utils.fail(e, op))

    def getOrganizationDescriptor(self) -> OrganizationDescriptor:
        return OrganizationDescriptor(self.describe_organization())

    def getAccountDescriptor(self, accountId) -> AccountDescriptor:
        return AccountDescriptor(self.describe_account(accountId))
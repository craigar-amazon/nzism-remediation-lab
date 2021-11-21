import botocore

from lib.rdq import RdqError
from .base import ServiceUtils


def _canon_alias(aliasName):
    return "alias/"+aliasName

class KmsClient:
    def __init__(self, profile):
        service = 'kms'
        self._profile = profile
        self._client = profile.getClient(service)
        self._utils = ServiceUtils(profile, service)

    def policy_statement_default(self):
        sid = "Enable IAM policies"
        principalArn = "arn:aws:iam::{}:root".format(self._profile.accountId)
        return {
            'Sid': sid,
            'Effect': "Allow",
            'Principal': {
                'AWS': principalArn
            },
            'Action': "kms:*",
            'Resource': "*" 
        }

    def describe_key(self, keyId):
        op = 'describe_key'
        try:
            response = self._client.describe_key(
                KeyId=keyId
            )
            return response['KeyMetadata']
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return None
            raise RdqError(self._utils.fail(e, op, 'KeyId', keyId))

    def create_key_arn(self, description, policyJson):
        op = 'create_key'
        try:
            response = self._client.create_key(
                KeySpec="SYMMETRIC_DEFAULT",
                Description=description,
                Policy=policyJson
            )
            return response['KeyMetadata']['Arn']
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'Description', description))

    def create_alias(self, aliasName, cmkArn):
        op = 'create_alias'
        try:
            self._client.create_alias(
                AliasName=aliasName,
                TargetKeyId=cmkArn
            )
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'AliasName', aliasName, 'CmkArn', cmkArn))

    def get_key_policy(self, cmkArn):
        op = 'get_key_policy'
        try:
            response = self._client.get_key_policy(
                KeyId=cmkArn,
                PolicyName='default'
            )
            return response['Policy']
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'CmkArn', cmkArn))

    def put_key_policy(self, cmkArn, policyJson):
        op = 'put_key_policy'
        try:
            self._client.put_key_policy(
                KeyId=cmkArn,
                PolicyName='default',
                Policy=policyJson
            )
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'CmkArn', cmkArn))

    def get_key_rotation_status(self, cmkArn):
        op = 'get_key_rotation_status'
        try:
            response = self._client.get_key_rotation_status(
                KeyId=cmkArn
            )
            return response['KeyRotationEnabled']
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'CmkArn', cmkArn))


    def update_key_description(self, cmkArn, description):
        op = 'update_key_description'
        try:
            self._client.update_key_description(
                KeyId=cmkArn,
                Description=description
            )
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'CmkArn', cmkArn))

    def enable_key_rotation(self, cmkArn):
        op = 'enable_key_rotation'
        try:
            self._client.enable_key_rotation(
                KeyId=cmkArn
            )
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'CmkArn', cmkArn))

    def schedule_key_deletion(self, cmkArn, pendingWindowInDays):
        op = 'schedule_key_deletion'
        try:
            self._client.schedule_key_deletion(
                KeyId=cmkArn,
                PendingWindowInDays=pendingWindowInDays
            )
            return True
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return False
            raise RdqError(self._utils.fail(e, op, 'CmkArn', cmkArn))

    def delete_alias(self, canonAlias):
        op = 'delete_alias'
        try:
            self._client.delete_alias(
                AliasName=canonAlias
            )
            return True
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return False
            raise RdqError(self._utils.fail(e, op, 'AliasName', canonAlias))

    def declareCMKArn(self, description, alias, policyStatements):
        statements = [self.policy_statement_default()]
        statements.extend(policyStatements)
        policyMap = self._utils.policy_map(statements)
        reqdPolicyJson = self._utils.to_json(policyMap)
        canonAlias = _canon_alias(alias)
        exMeta = self.describe_key(canonAlias)
        createReqd = False
        if exMeta:
            keyState = exMeta['KeyState']
            if keyState == 'PendingDeletion':
                createReqd = True
            elif keyState == 'Enabled':
                createReqd = False
            else:
                erm = 'KMS CMK {} in unexpected state {}'.format(alias, keyState)
                raise RdqError(erm)
        else:
            createReqd = True
        if createReqd:
            newArn = self.create_key_arn(description, reqdPolicyJson)
            self.create_alias(canonAlias, newArn)
            self.enable_key_rotation(newArn)
            return newArn
        exArn = exMeta['Arn']
        exDescription = exMeta['Description']
        exPolicyJson = self._utils.to_json(self.get_key_policy(exArn))
        if exPolicyJson != reqdPolicyJson:
            self.put_key_policy(exArn, reqdPolicyJson)
        if exDescription != description:
            self.update_key_description(exArn, description)
        isRotationEnabled = self.get_key_rotation_status(exArn)
        if not isRotationEnabled:
            self.enable_key_rotation(exArn)
        return exArn

    def deleteCMK(self, alias, pendingWindowInDays=7):
        canonAlias = _canon_alias(alias)
        exMeta = self.describe_key(canonAlias)
        if exMeta:
            exArn = exMeta['Arn']
            self.delete_alias(canonAlias)
            self.schedule_key_deletion(exArn, pendingWindowInDays)

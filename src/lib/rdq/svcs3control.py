import botocore
from lib.rdq import RdqError
from lib.rdq.base import ServiceUtils

class S3ControlClient:
    def __init__(self, profile):
        service = 's3control'
        self._profile = profile
        self._client = profile.getClient(service)
        self._utils = ServiceUtils(profile, service)

    def get_public_access_block(self, accountId):
        op = 'get_public_access_block'
        try:
            response = self._client.get_public_access_block(
                AccountId=accountId
            )
            return response['PublicAccessBlockConfiguration']
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'AccountId', accountId))

    # PREVIEW
    def put_public_access_block(self, accountId, cfg):
        op = 'put_public_access_block'
        accountId = self._profile.accountId
        args = {
            'AccountId': accountId,
            'PublicAccessBlockConfiguration': cfg
        }
        if self._utils.preview(op, args): return
        try:
            self._client.put_public_access_block(
                PublicAccessBlockConfiguration=cfg,
                AccountId=accountId
            )
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'AccountId', accountId))

    # PREVIEW
    def declarePublicAccessBlock(self, targetAccountId=None, requiredState=True):
        accountId = targetAccountId if targetAccountId else self._profile.accountId
        keys = ['BlockPublicAcls', 'IgnorePublicAcls', 'BlockPublicPolicy', 'RestrictPublicBuckets']
        exMap = self.get_public_access_block(accountId)
        delta = False
        for key in keys:
            if key in exMap:
                exValue = exMap[key]
                if exValue != requiredState:
                    delta = True
            else:
                delta = True
        if not delta: return False
        cfg = {}
        for key in keys:
            cfg[key] = requiredState
        self.put_public_access_block(accountId, cfg)
        return True

import botocore

from .base import ServiceUtils

class S3ControlClient:
    def __init__(self, profile):
        service = 's3control'
        self._profile = profile
        self._client = profile.getClient(service)
        self._utils = ServiceUtils(profile, service)

    def get_public_access_block(self):
        op = 'get_public_access_block'
        accountId = self._profile.accountId
        try:
            response = self._client.get_public_access_block(
                AccountId=accountId
            )
            return response['PublicAccessBlockConfiguration']
        except botocore.exceptions.ClientError as e:
            raise Exception(self._utils.fail(e, op, 'AccountId', accountId))

    def put_public_access_block(self, cfg):
        op = 'put_public_access_block'
        accountId = self._profile.accountId
        try:
            self._client.put_public_access_block(
                PublicAccessBlockConfiguration=cfg,
                AccountId=accountId
            )
        except botocore.exceptions.ClientError as e:
            raise Exception(self._utils.fail(e, op, 'AccountId', accountId))

    def declarePublicAccessBlock(self):
        keys = ['BlockPublicAcls', 'IgnorePublicAcls', 'BlockPublicPolicy', 'RestrictPublicBuckets']
        exMap = self.get_public_access_block()
        delta = False
        for key in keys:
            if key in exMap:
                exValue = exMap[key]
                if not exValue:
                    delta = True
            else:
                delta = True
        if not delta: return False
        cfg = {}
        for key in keys:
            cfg[key] = True
        self.put_public_access_block(cfg)
        return True

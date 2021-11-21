import botocore
from lib.rdq import RdqError
from .base import ServiceUtils

class SQSClient:
    def __init__(self, profile):
        service = 'sqs'
        self._profile = profile
        self._client = profile.getClient(service)
        self._utils = ServiceUtils(profile, service)

    def _resource_arn(self, queueName):
        return self._profile.getRegionAccountArn('sqs', queueName)

    def _policy_statement_default(self, queueName):
        sid = "Enable IAM policies"
        principalArn = self._profile.getAccountPrincipalArn()
        resourceArn = self._resource_arn(queueName)
        return {
            'Sid': sid,
            'Effect': "Allow",
            'Principal': {
                'AWS': principalArn
            },
            'Action': "sqs:*",
            'Resource': resourceArn
        }

    def get_queue_url(self, queueName):
        op = 'get_queue_url'
        try:
            response = self._client.get_queue_url(
                QueueName=queueName
            )
            return response['QueueUrl']
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return None
            raise RdqError(self._utils.fail(e, op, 'QueueName', queueName))

    def get_queue_attributes(self, queueUrl, anames):
        op = 'get_queue_attributes'
        try:
            response = self._client.get_queue_attributes(
                QueueUrl=queueUrl,
                AttributeNames=anames
            )
            return response['Attributes']
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'QueueUrl', queueUrl))

    # PREVIEW
    def set_queue_attributes(self, queueUrl, deltaMap):
        op = 'set_queue_attributes'
        args = {
            'QueueUrl': queueUrl,
            'Attributes': deltaMap
        }
        if self._utils.preview(op, args): return
        try:
            self._client.set_queue_attributes(
                QueueUrl=queueUrl,
                Attributes=deltaMap
            )
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'QueueUrl', queueUrl))

    # PREVIEW
    def delete_queue(self, queueUrl):
        op = 'delete_queue'
        args = {
            'QueueUrl': queueUrl
        }
        if self._utils.preview(op, args): return True
        try:
            self._client.delete_queue(
                QueueUrl=queueUrl
            )
            return True
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return False
            raise RdqError(self._utils.fail(e, op, 'QueueUrl', queueUrl))

    # PREVIEW
    def create_queue(self, queueName, reqd):
        op = 'create_queue'
        args = {
            'QueueName': queueName,
            'Attributes': reqd
        }
        if self._utils.preview(op, args): return True
        try:
            self._client.create_queue(
                QueueName=queueName,
                Attributes=reqd
            )
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'QueueName', queueName))

    #PREVIEW
    def declareQueue(self, queueName, kmsMasterKeyId, policyStatements, visibilityTimeoutSecs):
        statements = [self._policy_statement_default(queueName)]
        statements.extend(policyStatements)
        policyMap = self._utils.policy_map(statements)
        policyJson = self._utils.to_json(policyMap)
        resourceArn = self._resource_arn(queueName)
        anames = ['KmsMasterKeyId', 'Policy', 'VisibilityTimeout']
        reqdMap = {
            'KmsMasterKeyId': kmsMasterKeyId,
            'Policy': policyJson,
            'VisibilityTimeout': str(visibilityTimeoutSecs)
        }
        exUrl = self.get_queue_url(queueName)
        if not exUrl:
            self.create_queue(queueName, reqdMap)
            self._utils.sleep(1)
            return resourceArn
        
        exMap = self.get_queue_attributes(exUrl, anames)
        deltaMap = {}
        exCanonMap = dict(exMap)
        exCanonMap['Policy'] = self._utils.to_json(exMap['Policy'])
        for aname in anames:
            delta = True
            if aname in exCanonMap:
                if exCanonMap[aname] == reqdMap[aname]:
                    delta = False
            if delta:
                deltaMap[aname] = reqdMap[aname]

        if bool(deltaMap):
            self.set_queue_attributes(exUrl, deltaMap)
        return resourceArn
        

    # PREVIEW
    def deleteQueue(self, queueName):
        exUrl = self.get_queue_url(queueName)
        if exUrl:
            self.delete_queue(exUrl)

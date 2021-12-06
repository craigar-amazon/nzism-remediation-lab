import botocore

from lib.base import Tags, DeltaBuild
from lib.rdq import RdqError
from lib.rdq.base import ServiceUtils

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

    def list_queue_tags(self, queueUrl):
        op = 'list_queue_tags'
        try:
            response = self._client.list_queue_tags(
                QueueUrl=queueUrl
            )
            return Tags(response['Tags'], queueUrl)
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'QueueUrl', queueUrl))

    # PREVIEW
    def set_queue_attributes(self, queueUrl, delta):
        op = 'set_queue_attributes'
        args = {
            'QueueUrl': queueUrl,
            'Attributes': delta
        }
        if self._utils.preview(op, args): return
        try:
            self._client.set_queue_attributes(
                QueueUrl=queueUrl,
                Attributes=delta
            )
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'QueueUrl', queueUrl))

    #PREVIEW
    def tag_queue(self, queueUrl, tags):
        op = 'tag_queue'
        args = {
            'QueueUrl': queueUrl,
            'Attributes': tags.toDict()
        }
        if self._utils.preview(op, args): return
        try:
            self._client.tag_queue(
                QueueUrl=queueUrl,
                Tags=tags.toDict()
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
    def create_queue(self, queueName, rq, tags):
        op = 'create_queue'
        args = {
            'QueueName': queueName,
            'Attributes': rq,
            'tags': tags.toDict()
        }
        if self._utils.preview(op, args): return True
        try:
            self._client.create_queue(
                QueueName=queueName,
                Attributes=rq,
                tags=tags.toDict()
            )
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'QueueName', queueName))

    #PREVIEW
    def declareQueueArn(self, queueName, kmsMasterKeyId, policyStatements, visibilityTimeoutSecs, tags):
        statements = [self._policy_statement_default(queueName)]
        statements.extend(policyStatements)
        policyMap = self._utils.policy_map(statements)
        resourceArn = self._resource_arn(queueName)

        db = DeltaBuild()
        db.putRequired('KmsMasterKeyId', kmsMasterKeyId)
        db.putRequiredJson('Policy', policyMap)
        db.putRequiredString('VisibilityTimeout', visibilityTimeoutSecs)
        rq = db.required()
        exUrl = self.get_queue_url(queueName)
        if not exUrl:
            self.create_queue(queueName, rq, tags)
            self._utils.sleep(1)
            return resourceArn        
        rqKeys = db.requiredKeys()
        exMap = self.get_queue_attributes(exUrl, rqKeys)
        db.loadExisting(exMap)
        db.normaliseExistingJson('Policy')
        delta = db.delta()
        if delta:
            self.set_queue_attributes(exUrl, delta)
        exTags = self.list_queue_tags(exUrl)
        deltaTags = tags.subtract(exTags)
        if not deltaTags.isEmpty():
            self.tag_queue(exUrl, deltaTags)
        return resourceArn
        

    # PREVIEW
    def deleteQueue(self, queueName):
        exUrl = self.get_queue_url(queueName)
        if exUrl:
            self.delete_queue(exUrl)

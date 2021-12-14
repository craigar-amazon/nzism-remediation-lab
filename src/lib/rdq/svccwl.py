import json
import botocore

from lib.base import Tags
from lib.rdq import RdqError
from lib.rdq.base import ServiceUtils

class LogGroupDescriptor:
    def __init__(self, base, tags :Tags):
        self._base = base
        self._tags = tags

    @property
    def arn(self):
        return self._base['arn']

    @property
    def logGroupName(self):
        return self._base['logGroupName']

    @property
    def kmsArn(self) -> str:
        return self._base.get('kmsKeyId')

    @property
    def retentionInDays(self) -> int:
        return self._base.get('retentionInDays')

    @property
    def tags(self) -> Tags:
        return self._tags

    def __str__(self):
        return json.dumps({
            'base': self._base,
            'tags': self._tags
        })

class CwlClient:
    def __init__(self, profile, maxAttempts=10):
        service = 'logs'
        self._profile = profile
        self._client = profile.getClient(service)
        self._utils = ServiceUtils(profile, service, maxAttempts)

    def describe_log_group(self, logGroupName):
        op = "describe_log_groups"
        try:
            paginator = self._client.get_paginator(op)
            page_iterator = paginator.paginate(logGroupNamePrefix=logGroupName)
            results = []
            for page in page_iterator:
                items = page["logGroups"]
                for item in items:
                    results.append(item)
            resultCount = len(results)
            if resultCount == 0: return None
            if resultCount == 1: return results[0]
            raise RdqError(self._utils.integrity("Multiple log groups for name", "LogGroupName", logGroupName, "MatchCount", resultCount))
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return None
            raise RdqError(self._utils.fail(e, op, 'LogGroupName', logGroupName))

    def list_log_group_tags(self, logGroupName):
        op = 'list_tags_log_group'
        try:
            response = self._client.list_tags_log_group(
                logGroupName=logGroupName
            )
            return response['tags']
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return None
            raise RdqError(self._utils.fail(e, op, 'LogGroupName', logGroupName))

    #PREVIEW
    def tag_log_group(self, logGroupName, tags :Tags):
        op = 'tag_log_group'
        args = {
            'LogGroupName': logGroupName,
            'Tags' : tags.toDict()
        }
        if self._utils.preview(op, args): return
        try:
            self._client.tag_log_group(
                logGroupName=logGroupName,
                tags=tags.toDict()
            )
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return
            raise RdqError(self._utils.fail(e, op, 'LogGroupName', logGroupName))

    #PREVIEW
    def associate_kms_key(self, logGroupName, kmsArn):
        op = 'associate_kms_key'
        args = {
            'LogGroupName': logGroupName,
            'KmsKeyId' : kmsArn
        }
        if self._utils.preview(op, args): return
        try:
            self._client.associate_kms_key(
                logGroupName=logGroupName,
                kmsKeyId=kmsArn
            )
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return
            raise RdqError(self._utils.fail(e, op, 'LogGroupName', logGroupName, 'KmsKeyId', kmsArn))

    #PREVIEW
    def disassociate_kms_key(self, logGroupName):
        op = 'disassociate_kms_key'
        args = {
            'LogGroupName': logGroupName
        }
        if self._utils.preview(op, args): return
        try:
            self._client.disassociate_kms_key(
                logGroupName=logGroupName
            )
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return
            raise RdqError(self._utils.fail(e, op, 'LogGroupName', logGroupName))


    def getLogGroupDescriptor(self, logGroupName :str) -> LogGroupDescriptor:
        exBase = self.describe_log_group(logGroupName)
        if not exBase: return None
        optTagDict = self.list_log_group_tags(logGroupName)
        exTags = Tags(optTagDict, logGroupName)
        return LogGroupDescriptor(exBase, exTags)

    #PREVIEW
    def associateKmsKeyWithLogGroup(self, logGroupName :str, cmkArn :str):
        self.associate_kms_key(logGroupName, cmkArn)

    #PREVIEW
    def disassociateKmsKeyWithLogGroup(self, logGroupName :str):
        self.associate_kms_key(logGroupName)

    #PREVIEW
    def putTags(self, logGroupName: str, tags :Tags):
        self.tag_log_group(logGroupName, tags)

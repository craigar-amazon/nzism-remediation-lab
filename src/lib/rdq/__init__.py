import logging
import botocore
import boto3

import lib.base as base

def _role_arn(accountId, roleName):
    return "arn:aws:iam::{}:role/{}".format(accountId, roleName)

class RdqError(Exception):
    def __init__(self, message):
        self._message = message

    def __str__(self):
        return self._message
    
    @property
    def message(self):
        return self._message


class Profile:
    def __init__(self, srcSession=None, roleName=None, sessionName=None, regionName=None):
        session = srcSession
        if not session:
            if regionName:
                session = boto3.Session(region_name=regionName)
            else:
                session = boto3.Session()
        self._sts_client = session.client('sts')
        self._tag_client = session.client('resourcegroupstaggingapi')
        op = "sts:get_caller_identity"
        try:
            r = self._sts_client.get_caller_identity()
            self._userId = r['UserId']
            self._accountId = r['Account']
            self._arn = r['Arn']
            self._session = session
            self._regionName = session.region_name
            self._roleName = roleName if roleName else session.profile_name
            self._sessionName = sessionName if sessionName else "Initial"
            self._isPreviewing = False
            self._previewLog = []
        except botocore.exceptions.NoCredentialsError as e:
            raise RdqError("Unable to locate credentials")
        except botocore.exceptions.ClientError as e:
            erc = e.response['Error']['Code'] 
            if erc == 'ExpiredToken':
                raise RdqError("Your credentials have expired")
            logging.error("botocore ClientError | Cause: %s | Api: %s | Detail %s", erc, op, e)
            raise RdqError("Your credentials are invalid")
    
    @property
    def accountId(self):
        return self._accountId

    @property
    def regionName(self):
        return self._regionName

    @property
    def sessionName(self):
        return self._sessionName

    def getClient(self, serviceName):
        return self._session.client(serviceName)

    def getAccountPrincipalArn(self):
        return "arn:aws:iam::{}:root".format(self._accountId)

    def getRegionAccountArn(self, serviceName, resourceName):
        return "arn:aws:{}:{}:{}:{}".format(serviceName, self._regionName, self._accountId, resourceName)

    def getGlobalAccountArn(self, serviceName, resourceName):
        return "arn:aws:{}::{}:{}".format(serviceName, self._accountId, resourceName)

    def getRoleArn(self, roleName):
        return _role_arn(self._accountId, roleName)

    def assumeRole(self, accountId, roleName, regionName, sessionName, durationSecs=3600):
        roleArn = _role_arn(accountId, roleName)
        op = "sts:assume_role"
        try:
            response = self._sts_client.assume_role(
                RoleArn=roleArn,
                RoleSessionName=sessionName,
                DurationSeconds=durationSecs
            )
            r = response['Credentials']
            newSession = boto3.Session(
                aws_access_key_id=r['AccessKeyId'],
                aws_secret_access_key=r['SecretAccessKey'],
                aws_session_token=r['SessionToken'],
                region_name = regionName
            )
            newProfile = Profile(newSession, roleName, sessionName)
            return newProfile
        except botocore.exceptions.ClientError as e:
            erc = e.response['Error']['Code'] 
            ectx = {
                'TargetRoleArn': roleArn,
                'TargetSessionName': sessionName,
                'TargetRegionName': regionName,
                'FromAccount': self._accountId,
                'FromRoleName': self._roleName,
                'FromSessionName': self._sessionName,
                'FromRegionName': self._regionName
            }
            logging.error("botocore ClientError | Cause: %s | Api: %s | Context: %s | Detail %s", erc, op, ectx, e)
            erm = "Role {} Account {} could not assume role {}".format(self._roleName, self._accountId, roleArn)
            raise RdqError(erm)

    def _tag_resources(self, arnList, tags):
        op = 'resourcegroupstaggingapi:tag_resources'
        ectx = {
            'ArnList': arnList,
            'Tags': tags.toDict(),
            'FromAccount': self._accountId,
            'FromRoleName': self._roleName,
            'FromRegionName': self._regionName
        }
        try:
            response = self._tag_client.tag_resources(
                ResourceARNList=arnList,
                Tags=tags.toDict()
            )
            failMap = response['FailedResourcesMap']
            if len(failMap) == 0: return True
            logging.error("Tagging Failure | FailedResponseMap: %s | Api: %s | Context: %s", failMap, op, ectx)
            return False
        except botocore.exceptions.ClientError as e:
            erc = e.response['Error']['Code']
            logging.error("botocore ClientError | Cause: %s | Api: %s | Context: %s | Detail %s", erc, op, ectx, e)
            return False

    def applyTagsToArn(self, arn, tags):
        if tags.isEmpty(): return True
        return self._tag_resources([arn], tags)

    def enablePreview(self, enable=True):
        exLog = self._previewLog
        self._isPreviewing = enable
        self._previewLog = []
        return exLog

    @property
    def isPreviewing(self):
        return self._isPreviewing

    def preview(self, op, args):
        if not self._isPreviewing: return False
        rec = {'api': op, 'args': args}
        self._previewLog.append(rec)
        return True

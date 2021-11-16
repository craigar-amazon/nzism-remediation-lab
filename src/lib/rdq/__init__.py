import botocore
import boto3

def _role_arn(accountId, roleName):
    return "arn:aws:iam::{}:role/{}".format(accountId, roleName)

class Profile:
    def __init__(self, srcSession=None, roleName=None, sessionName=None, regionName=None):
        session = srcSession
        if not session:
            if regionName:
                session = boto3.Session(region_name=regionName)
            else:
                session = boto3.Session()
        try:
            sts_client = session.client('sts')
            r = sts_client.get_caller_identity()
            self._userId = r['UserId']
            self._accountId = r['Account']
            self._arn = r['Arn']
            self._session = session
            self._regionName = session.region_name
            self._roleName = roleName if roleName else session.profile_name
            self._sessionName = sessionName if sessionName else "Initial"
        except botocore.exceptions.ClientError as e:
            erc = e.response['Error']['Code'] 
            if erc == 'ExpiredToken':
                raise Exception("Your credentials have expired")
            print("Unexpected error calling sts.get_caller_identity")
            print(e)
            raise Exception("Your credentials are invalid")

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

    def getRegionAccountArn(self, serviceName, resourceName):
        return "arn:aws:{}:{}:{}:{}".format(serviceName, self._regionName, self._accountId, resourceName)

    def getGlobalAccountArn(self, serviceName, resourceName):
        return "arn:aws:{}::{}:{}".format(serviceName, self._accountId, resourceName)

    def getRoleArn(self, roleName):
        return _role_arn(self._accountId, roleName)

    def assumeRole(self, accountId, roleName, regionName, sessionName, durationSecs=3600):
        roleArn = _role_arn(accountId, roleName)
        try:
            sts_client = self._session.client('sts')
            response = sts_client.assume_role(
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
            print("Unexpected error calling sts.assume_role")
            print("TargetRoleArn: {}".format(roleArn))
            print("TargetSessionName: {}".format(sessionName))
            print("TargetRegionName: {}".format(regionName))
            print('FromAccount: {}'.format(self._accountId))
            print('FromRoleName: {}'.format(self._roleName))
            print('FromSessionName: {}'.format(self._sessionName))
            print('FromRegionName: {}'.format(self._regionName))
            print(e)
            erm = "Role {} Account {} could not assume role {}".format(self._roleName, self._accountId, roleArn)
            raise Exception(erm)

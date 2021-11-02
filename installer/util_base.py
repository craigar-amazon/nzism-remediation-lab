import botocore
import boto3.session as session

class Context:
    def __init__(self, regionName='ap-southeast-2'):
        self._regionName = regionName
        self._session= session.Session(region_name=regionName)
        try:
            sts_client = self._session.client('sts')
            r = sts_client.get_caller_identity()
            self._userId = r['UserId']
            self._accountId = r['Account']
            self._arn = r['Arn']
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
    def session(self):
        return self._session

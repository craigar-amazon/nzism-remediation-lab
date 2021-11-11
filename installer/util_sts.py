import botocore
import boto3

def assumeRole(session, roleArn, roleSessionName):
    try:
        iam_client = session.client('sts')
        response = iam_client.assume_role(
            RoleArn=roleArn,
            RoleSessionName=roleSessionName,
            DurationSeconds=3600
        )
        r = response['Credentials']
        session = boto3.Session(
            aws_access_key_id=r['AccessKeyId'],
            aws_secret_access_key=r['SecretAccessKey'],
            aws_session_token=r['SessionToken']
        )
        return session
    except botocore.exceptions.ClientError as e:
        print("Failed to iam.assume_role")
        print("roleArn: "+roleArn)
        print(e)
        return None

import botocore
import boto3

def validCMKARN(keyId):
    try:
        kms_client = boto3.client('kms')
        response = kms_client.describe_key(KeyId=keyId)
        r = response['KeyMetadata']
        if r["Enabled"]: return r["Arn"]
        return ''
    except botocore.exceptions.ClientError as e:
        print("Failed to describe_key")
        print(e)
        print("KeyId="+keyId)
        return ''

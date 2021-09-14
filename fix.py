import botocore
import boto3

def associateCMKWithCWLG(cwlgName, cmkArn):
    try:
        cwl_client = boto3.client('logs')
        response = cwl_client.associate_kms_key(logGroupName=cwlgName, kmsKeyId=cmkArn)
        return True
    except botocore.exceptions.ClientError as e:
        print("Failed to associate_kms_key")
        print(e)
        print("logGroupName="+cwlgName)
        print("kmsKeyId="+cmkArn)
        return False

def cwlgPutRetentionPolicy(cwlgName, retentionInDays):
    try:
        cwl_client = boto3.client('logs')
        response = cwl_client.put_retention_policy(logGroupName=cwlgName, retentionInDays=retentionInDays)
        return True
    except botocore.exceptions.ClientError as e:
        print("Failed to put_retention_policy")
        print(e)
        print("logGroupName="+cwlgName)
        print("retentionInDays="+str(retentionInDays))
        return False

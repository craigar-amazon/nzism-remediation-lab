import botocore
import boto3

def applyCloudWatchLogGroupList(applyToCloudWatchLogGroup, cfg):
    cwl_client = boto3.client('logs')
    applyCount = 0
    paginator_log_groups = cwl_client.get_paginator("describe_log_groups")
    page_iterator_log_groups = paginator_log_groups.paginate()
    for page_log_groups in page_iterator_log_groups:
        log_groups = page_log_groups["logGroups"]
        for log_group in log_groups:
            if applyToCloudWatchLogGroup(log_group, cfg):
                applyCount += 1
    return applyCount


def applyS3BucketList(applyToS3Bucket, cfg):
    s3_client = boto3.client('s3')
    applyCount = 0
    response = s3_client.list_buckets()
    buckets = response['Buckets']
    for bucket in buckets:
        bucketName = bucket['Name']
        if applyToS3Bucket(bucketName, cfg):
            applyCount += 1
    return applyCount


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

# Allow s3:GetBucketPolicy
def getBucketPolicy(bucketName):
    try:
        s3_client = boto3.client('s3')
        response = s3_client.get_bucket_policy(Bucket=bucketName)
        r = response['Policy']
        print(r)
        return r
    except botocore.exceptions.ClientError as e:
        erc = e.response['Error']['Code']
        if erc == 'NoSuchBucketPolicy':
            return ''
        print("Failed to get_bucket_policy")
        print(e)
        print("Bucket="+bucketName)
        return ''

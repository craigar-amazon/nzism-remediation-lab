import os
import botocore
import boto3

def lambda_handler(event, context):
    (success, msg) = handler(event)
    if (success):
        print("Success: "+msg)
    else:
        print("Failed: "+msg)
    statusCode = 200 if success else 500
    return {
        'statusCode': statusCode,
        'body': msg
    }

def getCloudWatchLogsCMK():
    vname = 'CWL_CMK_ID'
    if vname in os.environ:
        return os.environ[vname]
    return ''

def getCloudWatchLogGroupMinRetentionDays():
    return 545

def handler(event):
    if not ("source" in event):
        return (False, "Missing source attribute")

    source = event["source"]
    if source == "aws.config": 
        return handler_config(event)

    if source == "scan":
        return handler_scan(event)

    return (False, "Unsupported source: "+source)


def handler_config(event):
    detail_type = event["detail-type"]
    if detail_type == "Config Rules Compliance Change":
        return compliance_change(event)

    return (True, "No action - "+detail_type)

def handler_scan(event):
    results = []
    results.append(scan_cloudwatch_log_groups(event))
    return (True, '|'.join(results))


def compliance_change(event):
    detail = event["detail"]
    resourceType = detail["resourceType"]
    newEvaluationResult = detail["newEvaluationResult"]
    if not ("complianceType" in newEvaluationResult):
        return (False, 'No Missing New Compliance Type')

    complianceType = newEvaluationResult["complianceType"]
    if not (complianceType == 'NON_COMPLIANT'):
        return (True, 'No action needed- ' + complianceType)

    rawConfigRuleName = detail["configRuleName"]
    pos_cr_prefix = rawConfigRuleName.find('-conformance-pack-')
    if pos_cr_prefix < 0:
        configRuleName = rawConfigRuleName
    else:
        configRuleName = rawConfigRuleName[:pos_cr_prefix]
    if resourceType == "AWS::Logs::LogGroup" and configRuleName == 'cloudwatch-log-group-encrypted':
        return compliance_cwlg_encrypted(event, detail)

    return (True, 'No remediation for '+configRuleName)

def scan_cloudwatch_log_groups(event):
    keyId = getCloudWatchLogsCMK()
    if len(keyId) == 0:
        return 'No CloudWatch Logs CMK Id Defined'

    cmkArn = validCMKARN(keyId)
    if len(cmkArn) == 0:
        return 'Invalid CMK Id '+keyId

    minRetentionDays = getCloudWatchLogGroupMinRetentionDays()

    cwl_client = boto3.client('logs')

    fixCount = 0
    paginator_log_groups = cwl_client.get_paginator("describe_log_groups")
    page_iterator_log_groups = paginator_log_groups.paginate()
    for page_log_groups in page_iterator_log_groups:
        log_groups = page_log_groups["logGroups"]
        for log_group in log_groups:
            if assert_cloudwatch_log_group(log_group, cmkArn, minRetentionDays):
                fixCount += 1

    return "Fixed {} cloudwatch log groups".format(fixCount)


def assert_cloudwatch_log_group(log_group, cmkArn, minRetentionDays):
    logGroupName = log_group["logGroupName"]
    delta = False
    fixCMK = not("kmsKeyId" in log_group)
    fixRetention = False
    if "retentionInDays" in log_group:
      retentionDays = int(log_group["retentionInDays"])
      fixRetention = retentionDays < minRetentionDays
    else:
        fixRetention = True
    if fixCMK:
        if associateCMKWithCWLG(logGroupName, cmkArn):
            delta = True
    if fixRetention:
        if cwlgPutRetentionPolicy(logGroupName, minRetentionDays):
            delta = True

    return delta


def compliance_cwlg_encrypted(event, detail):
    keyId = getCloudWatchLogsCMK()
    if len(keyId) == 0:
        return (False, 'No CloudWatch Logs CMK Id Defined')

    cmkArn = validCMKARN(keyId)
    if len(cmkArn) == 0:
        return (False, 'Invalid CMK Id '+keyId)

    resourceId = detail["resourceId"]

    if associateCMKWithCWLG(resourceId, cmkArn):
        return (True, 'Encrypted ' + resourceId + ' with ' + cmkArn)

    return (False, 'Failed to associate '+cmkArn + ' with ' +resourceId)


def validCMKARN(keyId):
    try:
        kms_client = boto3.client('kms')
        response = kms_client.describe_key(KeyId=keyId)
        r = response['KeyMetadata']
        if r["Enabled"]:
            return r["Arn"]
        return r
    except botocore.exceptions.ClientError as e:
        print("Failed to describe_key "+keyId)
        print(e)
        return ''

def associateCMKWithCWLG(cwlgName, cmkArn):
    try:
        cwl_client = boto3.client('logs')
        response = cwl_client.associate_kms_key(logGroupName=cwlgName, kmsKeyId=cmkArn)
        return True
    except botocore.exceptions.ClientError as e:
        print("Failed to associate_kms_key "+cmkArn+" with "+cwlgName)
        print(e)
        return False

def cwlgPutRetentionPolicy(cwlgName, retentionInDays):
    try:
        cwl_client = boto3.client('logs')
        response = cwl_client.put_retention_policy(logGroupName=cwlgName, retentionInDays=retentionInDays)
        return True
    except botocore.exceptions.ClientError as e:
        print("Failed to put_retention_policy "+retentionInDays+" with "+cwlgName)
        print(e)
        return False


def sample_event1():
    return {
    "version": "0",
    "id": "f6d29562-cddc-8302-80c9-1857d49fa132",
    "detail-type": "Config Rules Compliance Change",
    "source": "aws.config",
    "account": "775397712397",
    "time": "2021-09-10T03:32:10Z",
    "region": "ap-southeast-2",
    "resources": [],
    "detail": {
        "resourceId": "BadCrowd4",
        "awsRegion": "ap-southeast-2",
        "awsAccountId": "775397712397",
        "configRuleName": "cloudwatch-log-group-encrypted-conformance-pack-6cruwvtg2",
        "recordVersion": "1.0",
        "configRuleARN": "arn:aws:config:ap-southeast-2:775397712397:config-rule/aws-service-rule/config-conforms.amazonaws.com/config-rule-2pxv2c",
        "messageType": "ComplianceChangeNotification",
        "newEvaluationResult": {
            "evaluationResultIdentifier": {
                "evaluationResultQualifier": {
                    "configRuleName": "cloudwatch-log-group-encrypted-conformance-pack-6cruwvtg2",
                    "resourceType": "AWS::Logs::LogGroup",
                    "resourceId": "BadCrowd4"
                },
                "orderingTimestamp": "2021-09-10T03:31:54.168Z"
            },
            "complianceType": "NON_COMPLIANT",
            "resultRecordedTime": "2021-09-10T03:32:09.685Z",
            "configRuleInvokedTime": "2021-09-10T03:32:09.218Z",
            "annotation": "This log group is not encrypted."
        },
        "notificationCreationTime": "2021-09-10T03:32:10.176Z",
        "resourceType": "AWS::Logs::LogGroup"
    }
}

def sample_event2():
    return {
        "source": "scan"
    }

lambda_handler(sample_event2(), {})

from lambda_function import lambda_handler

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
        "resourceId": "Demo4",
        "awsRegion": "ap-southeast-2",
        "awsAccountId": "775397712397",
        "configRuleName": "cw-loggroup-retention-period-check-conformance-pack-6cruwvtg2",
        "recordVersion": "1.0",
        "configRuleARN": "arn:aws:config:ap-southeast-2:775397712397:config-rule/aws-service-rule/config-conforms.amazonaws.com/config-rule-2pxv2c",
        "messageType": "ComplianceChangeNotification",
        "newEvaluationResult": {
            "evaluationResultIdentifier": {
                "evaluationResultQualifier": {
                    "configRuleName": "cw-loggroup-retention-period-check-conformance-pack-6cruwvtg2",
                    "resourceType": "AWS::Logs::LogGroup",
                    "resourceId": "Demo4"
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

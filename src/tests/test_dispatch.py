import unittest
import json
from lambdas.core.ComplianceDispatcher.lambda_function import lambda_handler

def body1():
    return {
        "version": "0",
        "id": "f0eae78e-0ccc-4079-a509-206fca99c4fc",
        "detail-type": "Config Rules Compliance Change",
        "source": "aws.config",
        "account": "746869318262",
        "time": "2021-11-23T11:05:05Z",
        "region": "ap-southeast-2",
        "resources": [],
        "detail": {
            "resourceId": "NZISM-ComplianceDispatcher",
            "awsRegion": "ap-southeast-2",
            "awsAccountId": "746869318262",
            "configRuleName": "lambda-function-public-access-prohibited-conformance-pack-qayjyopmd",
            "recordVersion": "1.0",
            "configRuleARN": "arn:aws:config:ap-southeast-2:746869318262:config-rule/aws-service-rule/config-conforms.amazonaws.com/config-rule-axgui2",
            "messageType": "ComplianceChangeNotification",
            "newEvaluationResult": {
                "evaluationResultIdentifier": {
                    "evaluationResultQualifier": {
                        "configRuleName": "lambda-function-public-access-prohibited-conformance-pack-qayjyopmd",
                        "resourceType": "AWS::Lambda::Function",
                        "resourceId": "NZISM-ComplianceDispatcher"
                    },
                    "orderingTimestamp": "2021-11-23T11:04:51.916Z"
                },
                "complianceType": "COMPLIANT",
                "resultRecordedTime": "2021-11-23T11:05:04.582Z",
                "configRuleInvokedTime": "2021-11-23T11:05:04.294Z"
            },
            "notificationCreationTime": "2021-11-23T11:05:05.374Z",
            "resourceType": "AWS::Lambda::Function"
        }
    }

def body2():
    return {
        "version": "0",
        "id": "a0eae78e-0ccc-4079-a509-206fca99c4fc",
        "detail-type": "Config Rules Compliance Change",
        "source": "aws.config",
        "account": "746869318262",
        "time": "2021-11-23T11:05:05Z",
        "region": "ap-southeast-2",
        "resources": [],
        "detail": {
            "resourceId": "119399605612",
            "awsRegion": "ap-southeast-2",
            "awsAccountId": "119399605612",
            "configRuleName": "s3-account-level-public-access-blocks-periodic-conformance-pack-qayjyopmd",
            "recordVersion": "1.0",
            "configRuleARN": "arn:aws:config:ap-southeast-2:119399605612:config-rule/aws-service-rule/config-conforms.amazonaws.com/config-rule-axgui2",
            "messageType": "ComplianceChangeNotification",
            "newEvaluationResult": {
                "evaluationResultIdentifier": {
                    "evaluationResultQualifier": {
                        "configRuleName": "s3-account-level-public-access-blocks-periodic-conformance-pack-qayjyopmd",
                        "resourceType": "AWS::Account",
                        "resourceId": "NZISM-ComplianceDispatcher"
                    },
                    "orderingTimestamp": "2021-11-23T11:04:51.916Z"
                },
                "complianceType": "NON_COMPLIANT",
                "resultRecordedTime": "2021-11-23T11:05:04.582Z",
                "configRuleInvokedTime": "2021-11-23T11:05:04.294Z"
            },
            "notificationCreationTime": "2021-11-23T11:05:05.374Z",
            "resourceType": "AWS::::Account"
        }
    }

def queuedMessage1(body):
    return {
        "messageId": "ec5a26d4-a9f2-4d1c-848e-b5672cce977e",
        "receiptHandle": "AQEBbM=",
        "body": json.dumps(body),
        "attributes": {
            "ApproximateReceiveCount": "1",
            "SentTimestamp": "1637665509689",
            "SenderId": "AIDAIDYJ7RPI7CT46XWPK",
            "ApproximateFirstReceiveTimestamp": "1637665509696"  
        },
        "messageAttributes": {},
        "md5OfBody": "a613118c76d48c345dafb54e9a847121",
        "eventSource": "aws:sqs",
        "eventSourceARN": "arn:aws:sqs:ap-southeast-2: 746869318262:NZISM-ComplianceChangeQueue",
        "awsRegion": "ap-southeast-2"
    }

def queuedMessage2(body):
    return {
        "messageId": "ab5a26d4-a9f2-4d1c-848e-b5672cce977e",
        "receiptHandle": "BQEBbM=",
        "body": json.dumps(body),
        "attributes": {
            "ApproximateReceiveCount": "1",
            "SentTimestamp": "1637665509689",
            "SenderId": "AIDAIDYJ7RPI7CT46XWPK",
            "ApproximateFirstReceiveTimestamp": "1637665509696"  
        },
        "messageAttributes": {},
        "md5OfBody": "a613118c76d48c345dafb54e9a847121",
        "eventSource": "aws:sqs",
        "eventSourceARN": "arn:aws:sqs:ap-southeast-2: 746869318262:NZISM-ComplianceChangeQueue",
        "awsRegion": "ap-southeast-2"
    }

class TestDispatch(unittest.TestCase):
    def test_dispatch(self):
        print("ACTION: Ensure credentials set to dispatching audit account")
        records = {
            'Records': [
                queuedMessage1(body1()),
                queuedMessage2(body2())
            ]
        }
        try:
            lambda_handler(records, {})
        except Exception as e:
            self.fail(e)


if __name__ == '__main__':
    loader = unittest.TestLoader()
    loader.testMethodPrefix = "test_dispatch"
    unittest.main(warnings='default', testLoader = loader)



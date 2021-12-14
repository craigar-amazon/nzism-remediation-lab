def awsLambdaBasicExecution():
    return "AWSLambdaBasicExecutionRole"

def trustLambda():
    return trustService(principalLambda())

def trustEventBridge():
    return trustService(principalEventBridge())

def principalLambda():
    return "lambda.amazonaws.com"

def principalEventBridge():
    return "events.amazonaws.com"

def serviceNamespaceSQS():
    return "sqs"

def trustService(servicePrincipalName):
    return {
        'Version': "2012-10-17",
        'Statement': [
            {
                'Effect': "Allow",
                'Principal': {
                    'Service': servicePrincipalName
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }

def trustAccount(accountId):
    return {
        'Version': "2012-10-17",
        'Statement': [
            {
                'Effect': "Allow",
                'Principal': {
                    'AWS': "arn:aws:iam::{}:root".format(accountId)
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }

def permissions(statements):
    return {
        'Version': "2012-10-17",
        'Statement': statements
    }

def allowConsumeSQS(queueArn, sid="ConsumeSQS"):
    return {
        'Sid': sid,
        'Effect': "Allow",
        'Action': [
            "sqs:ReceiveMessage",
            "sqs:DeleteMessage",
            "sqs:GetQueueAttributes"
        ],
        'Resource': queueArn
    }

def allowDecryptCMK(cmkArn, sid="DecryptCMK"):
    return {
        'Sid': sid,
        'Effect': "Allow",
        'Action': [
            "kms:Decrypt"
        ],
        'Resource': cmkArn
    }

def allowInvokeLambda(lambdaArn, sid="InvokeLambda"):
    return {
        'Sid': sid,
        'Effect': "Allow",
        'Action': [
            "lambda:InvokeFunction"
        ],
        'Resource': lambdaArn
    }

def allowDescribeIam(roleArn, sid="DescribeIam"):
    return {
        'Sid': sid,
        'Effect': "Allow",
        'Action': [
            "iam:GetRole"
        ],
        'Resource': roleArn
    }

def allowDescribeAccount(masterAccountId, organizationId, sid="DescribeAccount"):
    return {
        'Sid': sid,
        'Effect': "Allow",
        'Action': [
            "organizations:DescribeAccount"
        ],
        'Resource': "arn:aws:organizations::{}:account/{}/*".format(masterAccountId, organizationId)
    }

def allowCMKForServiceProducer(profile, storageServiceNamespace, producerServicePrincipal):
    sid = "Producer service " + producerServicePrincipal + " for " + storageServiceNamespace
    conditionKey = "kms:EncryptionContext:aws:{}:arn".format(storageServiceNamespace)
    conditionValue = "arn:aws:{}:{}:{}:*".format(storageServiceNamespace, profile.regionName, profile.accountId)
    return {
        'Sid': sid,
        'Effect': "Allow",
        'Principal': {
            'Service': producerServicePrincipal
        },
        'Action': [
            "kms:Decrypt",
            "kms:GenerateDataKey"

        ],
        'Resource': '*',
        'Condition': {
            'ArnLike': {
                conditionKey: conditionValue
            }
        }
    }

def allowSQSForServiceProducer(profile, queueName, producerServicePrincipal, sourceArn):
    sid = "Producer service " + producerServicePrincipal + " for SQS"
    resourceArn = profile.getRegionAccountArn('sqs', queueName)
    return {
        'Sid': sid,
        'Effect': "Allow",
        'Principal': {
            'Service': producerServicePrincipal
        },
        'Action': "sqs:SendMessage",
        'Resource': resourceArn,
        'Condition': {
            'ArnLike': {
                "aws:SourceArn": sourceArn
            }
        }
    }

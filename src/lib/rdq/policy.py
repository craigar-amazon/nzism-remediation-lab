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

def allowConsumeSQS(queueArn, sid='ConsumeSQS'):
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

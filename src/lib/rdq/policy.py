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

def allowSQSCMKForServiceProducer(profile, producerServicePrincipal):
    return allowCMKForServiceProducer(profile, 'sqs', producerServicePrincipal)

def allowCMKForServiceProducer(profile, storageServiceName, producerServicePrincipal):
    sid = "Producer service " + producerServicePrincipal + " for " + storageServiceName
    conditionKey = "kms:EncryptionContext:aws:{}:arn".format(storageServiceName)
    conditionValue = "arn:aws:{}:{}:{}:*".format(storageServiceName, profile.regionName, profile.accountId)
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

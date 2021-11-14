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

def allowConsumeSQS(queueArn):
    statement = {
        'Effect': "Allow",
        'Action': [
            "sqs:ReceiveMessage",
            "sqs:DeleteMessage",
            "sqs:GetQueueAttributes"
        ],
        'Resource': queueArn
    }
    return permissions([statement])
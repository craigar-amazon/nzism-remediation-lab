def awsLambdaBasicExecution():
    return "AWSLambdaBasicExecutionRole"

def trustLambda():
    return trustService("lambda.amazonaws.com")

def trustEventBridge():
    return trustService("events.amazonaws.com")


def trustService(serviceName):
    return {
        'Version': "2012-10-17",
        'Statement': [
            {
                'Effect': "Allow",
                'Principal': {
                    'Service': serviceName
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
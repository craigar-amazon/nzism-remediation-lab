import json
import botocore

def _fail(e, op, queueName, *args):
    print("Unexpected error calling sqs."+op)
    print("queueName: "+queueName)
    for a in args:
        print(a)
    print(e)
    return "Unexpected error calling {} on {}".format(op, queueName)

def _is_resource_not_found(e):
    return e.response['Error']['Code'] == 'QueueDoesNotExist'


def resource_arn(ctx, queueName):
    return "arn:aws:sqs:{}:{}:{}".format(ctx.regionName, ctx.accountId, queueName)

def policy_statement_default(ctx, queueName):
    sid = "Enable IAM policies"
    principalArn = "arn:aws:iam::{}:root".format(ctx.accountId)
    resourceArn = resource_arn(ctx, queueName)
    return {
        'Sid': sid,
        'Effect': "Allow",
        'Principal': {
            'AWS': principalArn
        },
        'Action': "sqs:*",
        'Resource': resourceArn
    }

def policy_map(statements):
    return {
    'Version': "2012-10-17",
    'Statement': statements
    }

def policyStatementEventbridge(ctx, queueName, ruleArn):
    sid = "Eventbridge Producer"
    resourceArn = resource_arn(ctx, queueName)
    return {
        'Sid': sid,
        'Effect': "Allow",
        'Principal': {
            'Service': "events.amazonaws.com"
        },
        'Action': [
            "sqs:SendMessage"
        ],
        'Resource': resourceArn,
        'Condition': {
            'ArnEquals': {
                "aws:SourceArn": ruleArn
            }
        }
    }

def create_queue_url(ctx, queueName, reqd):
    try:
        client = ctx.session.client('sqs')
        response = client.create_queue(
            QueueName=queueName,
            Attributes=reqd
        )
        return response['QueueUrl']
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'create_queue', queueName)
        raise Exception(erm)


def declareQueue(ctx, queueName, kmsMasterKeyId, policyStatements, visibilityTimeoutSecs):
    statements = [policy_statement_default(ctx, queueName)]
    statements.extend(policyStatements)
    policyMap = policy_map(statements)
    policyJson = json.dumps(policyMap)
    reqd = {
        'KmsMasterKeyId': kmsMasterKeyId,
        'Policy': policyJson,
        'VisibilityTimeout': str(visibilityTimeoutSecs)
    }
    newUrl = create_queue_url(ctx, queueName, reqd)
    return newUrl
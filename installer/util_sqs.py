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
    return e.response['Error']['Code'] == 'AWS.SimpleQueueService.NonExistentQueue'

def _normalisePolicy(src):
    return json.dumps(json.loads(src))

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
        'Action': "sqs:SendMessage",
        'Resource': resourceArn,
        'Condition': {
            'ArnEquals': {
                "aws:SourceArn": ruleArn
            }
        }
    }

def get_queue_url(ctx, queueName):
    try:
        client = ctx.session.client('sqs')
        response = client.get_queue_url(
            QueueName=queueName
        )
        return response['QueueUrl']
    except botocore.exceptions.ClientError as e:
        if _is_resource_not_found(e): return None
        erm = _fail(e, 'get_queue_url', queueName)
        raise Exception(erm)

def delete_queue(ctx, queueUrl):
    try:
        client = ctx.session.client('sqs')
        client.delete_queue(
            QueueUrl=queueUrl
        )
        return True
    except botocore.exceptions.ClientError as e:
        if _is_resource_not_found(e): return False
        erm = _fail(e, 'delete_queue', queueUrl)
        raise Exception(erm)


def get_queue_attributes(ctx, queueUrl, anames):
    try:
        client = ctx.session.client('sqs')
        response = client.get_queue_attributes(
            QueueUrl=queueUrl,
            AttributeNames=anames
        )
        return response['Attributes']
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'get_queue_attributes', queueUrl)
        raise Exception(erm)

def set_queue_attributes(ctx, queueUrl, deltaMap):
    try:
        client = ctx.session.client('sqs')
        client.set_queue_attributes(
            QueueUrl=queueUrl,
            Attributes=deltaMap
        )
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'set_queue_attributes', queueUrl)
        raise Exception(erm)

def create_queue(ctx, queueName, reqd):
    try:
        client = ctx.session.client('sqs')
        client.create_queue(
            QueueName=queueName,
            Attributes=reqd
        )
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'create_queue', queueName)
        raise Exception(erm)

def deleteQueue(ctx, queueName):
    exUrl = get_queue_url(ctx, queueName)
    if exUrl:
        delete_queue(ctx, exUrl)

def declareQueue(ctx, queueName, kmsMasterKeyId, policyStatements, visibilityTimeoutSecs):
    statements = [policy_statement_default(ctx, queueName)]
    statements.extend(policyStatements)
    policyMap = policy_map(statements)
    policyJson = json.dumps(policyMap)
    resourceArn = resource_arn(ctx, queueName)
    anames = ['KmsMasterKeyId', 'Policy', 'VisibilityTimeout']
    reqdMap = {
        'KmsMasterKeyId': kmsMasterKeyId,
        'Policy': policyJson,
        'VisibilityTimeout': str(visibilityTimeoutSecs)
    }
    exUrl = get_queue_url(ctx, queueName)
    if not exUrl:
        create_queue(ctx, queueName, reqdMap)
        return resourceArn
    
    exMap = get_queue_attributes(ctx, exUrl, anames)
    deltaMap = {}
    exCanonMap = dict(exMap)
    exCanonMap['Policy'] = _normalisePolicy(exMap['Policy'])
    for aname in anames:
        delta = True
        if aname in exCanonMap:
            if exCanonMap[aname] == reqdMap[aname]:
                delta = False
        if delta:
            deltaMap[aname] = reqdMap[aname]

    if bool(deltaMap):
        set_queue_attributes(ctx, exUrl, deltaMap)
    return resourceArn

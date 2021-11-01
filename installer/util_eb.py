import json
import botocore
import boto3

def _is_resource_not_found(e):
    return e.response['Error']['Code'] == 'ResourceNotFoundException'    

def _fail(e, op, eventBusName, ruleName):
    print("Unexpected error calling events."+op)
    print("eventBusName: "+eventBusName)
    if ruleName:
        print("ruleName: "+ruleName)
    print(e)
    return "Unexpected error calling {} on {}".format(op, eventBusName)

def put_eventbus_target(ctx, eventBusArn, ruleName, targetId, targetArn, maxAgeSeconds):
    try:
        client = ctx.session.client('events')
        client.put_targets(
            Rule=ruleName,
            EventBusName=eventBusArn,
            Targets = [
                {
                    'Id': targetId,
                    'Arn': targetArn,
                    'RetryPolicy':  {
                        'MaximumEventAgeInSeconds': maxAgeSeconds
                    }
                }
            ]
        )
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'put_targets', eventBusArn, ruleName)
        raise Exception(erm)


def getEventBus(ctx, eventBusName):
    try:
        client = ctx.session.client('events')
        response = client.describe_event_bus(
            Name=eventBusName
        )
        return response
    except botocore.exceptions.ClientError as e:
        if _is_resource_not_found(e): return None
        erm = _fail(e, 'describe_event_bus', eventBusName)
        raise Exception(erm)

def createEventBusArn(ctx, eventBusName):
    try:
        client = ctx.session.client('events')
        response = client.create_event_bus(
            Name=eventBusName
        )
        return response['EventBusArn']
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'create_event_bus', eventBusName)
        raise Exception(erm)

def deleteEventBusRule(ctx, eventBusName, ruleName):
    try:
        client = ctx.session.client('events')
        client.delete_rule(
            Name=ruleName,
            EventBusName=eventBusName
        )
        return True
    except botocore.exceptions.ClientError as e:
        if _is_resource_not_found(e): return False
        _fail(e, 'delete_rule', eventBusName, ruleName)
        return False

def deleteEventBus(ctx, eventBusName, ruleNames):
    try:
        for ruleName in ruleNames:
            deleteEventBusRule(eventBusName, ruleName)
        client = ctx.session.client('events')
        client.delete_event_bus(
            Name=eventBusName
        )
        return True
    except botocore.exceptions.ClientError as e:
        if _is_resource_not_found(e): return False
        _fail(e, 'delete_event_bus', eventBusName)
        return False

def declareEventBusArn(ctx, eventBusName):
    eventBus = getEventBus(ctx, eventBusName)
    if eventBus: return eventBus['Arn']
    return createEventBusArn(ctx, eventBusName)


def putEventBusPermissionForOrganization(ctx, eventBusName, organizationId):
    try:
        client = ctx.session.client('events')
        client.put_permission(
            EventBusName=eventBusName,
            Principal = '*',
            Action = 'events:PutEvents',
            StatementId = organizationId,
            Condition = {
                'Type': 'StringEquals',
                'Key': 'aws:PrincipalOrgID',
                'Value': organizationId
            }
        )
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'put_permission', eventBusName)
        raise Exception(erm)


# Allow events:PutRule
def putEventBusRuleArn(ctx, eventBusArn, ruleName, eventPatternMap, ruleDescription):
    eventPatternJson = json.dumps(eventPatternMap)
    try:
        client = ctx.session.client('events')
        response = client.put_rule(
            Name=ruleName,
            EventPattern=eventPatternJson,
            Description=ruleDescription, 
            EventBusName=eventBusArn
        )
        return response['RuleArn']
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'put_rule', eventBusArn, ruleName)
        raise Exception(erm)


def putEventBusLambdaTarget(ctx, eventBusArn, ruleName, lambdaArn, maxAgeSeconds):
    put_eventbus_target(ctx, eventBusArn, ruleName, 'Lambda', lambdaArn, maxAgeSeconds)

def putEventBusSQSTarget(ctx, eventBusArn, ruleName, sqsArn, maxAgeSeconds):
    put_eventbus_target(ctx, eventBusArn, ruleName, 'Queue', sqsArn, maxAgeSeconds)

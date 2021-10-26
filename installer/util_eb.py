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


def getEventBus(eventBusName):
    try:
        eb_client = boto3.client('events')
        response = eb_client.describe_event_bus(
            Name=eventBusName
        )
        return response
    except botocore.exceptions.ClientError as e:
        if _is_resource_not_found(e): return None
        erm = _fail(e, 'describe_event_bus', eventBusName)
        raise Exception(erm)

def createEventBusArn(eventBusName):
    try:
        eb_client = boto3.client('events')
        response = eb_client.create_event_bus(
            Name=eventBusName
        )
        return response['EventBusArn']
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'create_event_bus', eventBusName)
        raise Exception(erm)

def deleteEventBusRule(eventBusName, ruleName):
    try:
        eb_client = boto3.client('events')
        eb_client.delete_rule(
            Name=ruleName,
            EventBusName=eventBusName
        )
        return True
    except botocore.exceptions.ClientError as e:
        if _is_resource_not_found(e): return False
        _fail(e, 'delete_rule', eventBusName, ruleName)
        return False

def deleteEventBus(eventBusName, ruleNames):
    try:
        for ruleName in ruleNames:
            deleteEventBusRule(eventBusName, ruleName)
        eb_client = boto3.client('events')
        eb_client.delete_event_bus(
            Name=eventBusName
        )
        return True
    except botocore.exceptions.ClientError as e:
        if _is_resource_not_found(e): return False
        _fail(e, 'delete_event_bus', eventBusName)
        return False

def declareEventBusArn(eventBusName):
    eventBus = getEventBus(eventBusName)
    if eventBus: return eventBus['Arn']
    return createEventBusArn(eventBusName)


def putEventBusPermissionForOrganization(eventBusName, organizationId):
    try:
        eb_client = boto3.client('events')
        eb_client.put_permission(
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
def putEventBusRuleArn(eventBusArn, ruleName, eventPatternMap, ruleDescription):
    eventPatternJson = json.dumps(eventPatternMap)
    try:
        eb_client = boto3.client('events')
        response = eb_client.put_rule(
            Name=ruleName,
            EventPattern=eventPatternJson,
            Description=ruleDescription, 
            EventBusName=eventBusArn
        )
        return response['RuleArn']
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'put_rule', eventBusArn, ruleName)
        raise Exception(erm)

def putEventBusLambdaTarget(eventBusArn, ruleName, lambdaArn, maxAgeSeconds):
    try:
        eb_client = boto3.client('events')
        eb_client.put_targets(
            Rule=ruleName,
            EventBusName=eventBusArn,
            Targets = [
                {
                    'Id': 'Lambda',
                    'Arn': lambdaArn,
                    'RetryPolicy':  {
                        'MaximumEventAgeInSeconds': maxAgeSeconds
                    }
                }
            ]
        )
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'put_targets', eventBusArn, ruleName)
        raise Exception(erm)

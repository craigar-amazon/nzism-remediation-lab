import json
import botocore
import boto3

def getEventBus(eventBusName):
    try:
        eb_client = boto3.client('events')
        response = eb_client.describe_event_bus(
            Name=eventBusName
        )
        return response
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return None
        print("Failed to events.describe_event_bus")
        print("eventBusName: "+eventBusName)
        print(e)
        return None

def createEventBusArn(eventBusName):
    try:
        eb_client = boto3.client('events')
        response = eb_client.create_event_bus(
            Name=eventBusName
        )
        return response['EventBusArn']
    except botocore.exceptions.ClientError as e:
        print("Failed to events.create_event_bus")
        print("eventBusName: "+eventBusName)
        print(e)
        raise Exception("Could not create custom event bus '"+eventBusName+"'")

def deleteEventBus(eventBusName, ruleNames):
    try:
        eb_client = boto3.client('events')
        for ruleName in ruleNames:
            eb_client.delete_rule(
                Name=ruleName,
                EventBusName=eventBusName
            )
        eb_client.delete_event_bus(
            Name=eventBusName
        )
        return True
    except botocore.exceptions.ClientError as e:
        print("Failed to events.delete_event_bus")
        print("eventBusName: "+eventBusName)
        print(e)
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
        print("Failed to events.put_permission")
        print("eventBusName: "+eventBusName)
        print("organizationId: "+organizationId)
        print(e)
        raise Exception("Could not grant organization permission for custom event bus '"+eventBusName+"'")


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
        print("Failed to events.put_rule")
        print("eventBusArn: "+eventBusArn)
        print("ruleName: "+ruleName)
        print(e)
        raise Exception("Could not add rule to '"+eventBusArn+"' event bus")

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
        print("Failed to events.put_targets")
        print("eventBusArn: "+eventBusArn)
        print("ruleName: "+ruleName)
        print("lambdaArn: "+lambdaArn)
        print(e)
        raise Exception("Could not create lambda target for '"+ruleName+"' rule")



# Statement ID
# AWSEvents_NZISM-AutoRemediation_Id3be12590-0126-4525-934f-208560e21776
# Principal
# events.amazonaws.com
# Effect
# Allow
# Action
# lambda:InvokeFunction
# Conditions
# {
#  "ArnLike": {
#   "AWS:SourceArn": "arn:aws:events:ap-southeast-2:775397712397:rule/NZISM-AutoRemediation"
#  }
# }
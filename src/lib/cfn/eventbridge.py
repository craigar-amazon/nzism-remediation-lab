# IAM Policy Actions
iamPutEvents = "events:PutEvents"

iamPrincipal = {
    'Service': "events.amazonaws.com"
}

def EventPattern_ConfigComplianceChange():
    return {
        'source': ["aws.config"],
        'detail-type': ["Config Rules Compliance Change"]
        }

def Target(id, arn, roleArn):
    return {
        'Id': id,
        'Arn': arn,
        'RoleArn': roleArn
    }

def rRule(eventBusName, ruleName, eventPatternMap, targetList):
    return {
        'Type': "AWS::Events::Rule",
        'Properties': {
            'Name': ruleName,
            'EventBusName': eventBusName,
            'EventPattern': eventPatternMap,
            'Targets': targetList
        }
    }
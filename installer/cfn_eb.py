def eventPatternConfigComplianceChange():
    return {
        'source': ["aws.config"],
        'detail-type': ["Config Rules Compliance Change"]
        }

def propTarget(id, arn, roleArn):
    return {
        'Id': id,
        'Arn': arn,
        'RoleArn': roleArn
    }

def resourceRule(eventBusName, ruleName, eventPatternMap, targets):
    return {
        'Type': "AWS::Events::Rule",
        'Properties': {
            'Name': ruleName,
            'EventBusName': eventBusName,
            'EventPattern': eventPatternMap,
            'Targets': targets
        }
    }
import util_iam as ui
import util_lambda as ul
import util_eb as ue
import util_org as uo

def get_lambda_config():
    return {
        'Runtime': 'python3.8',
        'Handler': 'lambda_function.lambda_handler',
        'Timeout': 600,
        'Description': "Remediates non-compliant resources based on NZISM controls",
        'MemorySize': 128
    }

def get_assume_role_policy_json(roleName):
    return {
        'Version': "2012-10-17",
        'Statement': [
            {
                'Effect': "Allow",
                'Action': "sts:AssumeRole",
                'Resource': [
                    "arn:aws:iam::*:role/"+roleName
                ]
            }
        ]
    }

# lz1 = describeLandingZone(['Legacy-Production'])
# lz1 = describeLandingZone([], 'core', 'security', 'log-archive')

landingZone = uo.describeLandingZone()
organizationId = landingZone['OrganizationId']
print(organizationId)

lambdaFunctionName = "NZISMAutoRemediation"
lambdaRoleName = 'aws-controltower-AuditAdministratorRole'
lambdaRole = ui.getIamRole(lambdaRoleName)
if not lambdaRole:
    raise Exception('Required role '+lambdaRoleName+" does not exist")
lambdaCfg = get_lambda_config()
lambdaArn = ul.declareLambdaFunctionArn(lambdaFunctionName, lambdaRole['Arn'], lambdaCfg, './lambda')

eventBusName = 'NZISM-AutoRemediation'
ruleName = 'ComplianceChange'
ruleDescription = "Config Rule Compliance Change"
eventPattern = {
  'source': ["aws.config"],
  'detail-type': ["Config Rules Compliance Change"]
}
maxAgeSecs = 12 * 3600
ebArn = ue.declareEventBusArn(eventBusName)
ue.putEventBusPermissionForOrganization(eventBusName, organizationId)
print(ebArn)
ruleArn = ue.putEventBusRuleArn(ebArn, ruleName, eventPattern, ruleDescription)
ul.declareLambdaPolicyForEventRule(lambdaArn, ruleArn)

ue.putEventBusLambdaTarget(ebArn, ruleName, lambdaArn, maxAgeSecs)  

# deleteEventBus(eventBusName, [ruleName])




# payload = {
#     'source': "installer"
# }
# ul.invokeLambdaFunction("NZISMAutoRemediation", payload)




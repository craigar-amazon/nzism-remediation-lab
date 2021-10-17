import sys
import botocore
import boto3
from util_iam import getIamRole
from util_lambda import declareLambdaFunction
from util_lambda import invokeLambdaFunction

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


# lambdaRoleName = 'NZISMRemediationLambdaRole1'
# lambdaRoleDescription = 'Execution role for NZISM Remediation Lambda'
# memberRoleName = 'NZISMRemediationExecutionRole'

# role = declareLambdaIamRole(lambdaRoleName, lambdaRoleDescription)
# putRolePolicy(lambdaRoleName, "AssumeMemberExecutionRolePolicy", get_assume_role_policy_json(memberRoleName))
# lambdaCfg = get_lambda_config()
# declareLambdaFunction("NZISMAutoRemediation", role['Arn'], lambdaCfg, './lambda')

lambdaRoleName = 'aws-controltower-AuditAdministratorRole'
lambdaRole = getIamRole(lambdaRoleName)
if not lambdaRole:
    raise Exception('Required role '+lambdaRoleName+" does not exist")
lambdaCfg = get_lambda_config()
declareLambdaFunction("NZISMAutoRemediation", lambdaRole['Arn'], lambdaCfg, './lambda')

payload = {
    'source': "installer"
}

invokeLambdaFunction("NZISMAutoRemediation", payload)




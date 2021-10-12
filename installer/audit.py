import sys
import botocore
import boto3
from util_iam import declareLambdaIamRole
from util_iam import putRolePolicy
from util_lambda import declareLambdaFunction

def get_lambda_config():
    return {
        'Runtime': 'python3.8',
        'Handler': 'lambda_handler',
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

    
# role = createLambdaIamRole('/', 'NZISMRemediationLambdaRole1', 'Execution role for NZISM Remediation Lambda')
# print(role)

lambdaRoleName = 'NZISMRemediationLambdaRole1'
lambdaRoleDescription = 'Execution role for NZISM Remediation Lambda'
memberRoleName = 'NZISMRemediationExecutionRole'

role = declareLambdaIamRole(lambdaRoleName, lambdaRoleDescription)
putRolePolicy(lambdaRoleName, "AssumeMemberExecutionRolePolicy", get_assume_role_policy_json(memberRoleName))
lambdaCfg = get_lambda_config()
declareLambdaFunction("NZISMAutoRemediation", role['Arn'], lambdaCfg, './lambda')




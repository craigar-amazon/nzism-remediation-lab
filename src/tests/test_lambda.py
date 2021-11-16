from lib.rdq import Profile
from lib.rdq.svclambda import LambdaClient
from cmds.codeLoader import getTestCode
from lambdas.test.ApplyS3BPA.lambda_function import applyS3BPA

def test_s3bpa_direct(targetAccountId):
    event = {
        'target': {
            'awsAccountId': targetAccountId,
            'awsRegion': 'ap-southeast-2',
            'roleName': 'aws-controltower-AdministratorExecutionRole',
            'sessionName': 'Remediate-S3BPA',
            'configRuleName': 's3-account-level-public-access-blocks-periodic',
            'resourceType': 'AWS::::Account',
            'resourceId': targetAccountId
        }
    }
    profile = Profile()
    applyS3BPA(profile, targetAccountId, True)

def test_s3bpa_invoke(targetAccountId):
    event = {
        'target': {
            'awsAccountId': targetAccountId,
            'awsRegion': 'ap-southeast-2',
            'roleName': 'aws-controltower-AdministratorExecutionRole',
            'sessionName': 'Remediate-S3BPA',
            'configRuleName': 's3-account-level-public-access-blocks-periodic',
            'resourceType': 'AWS::::Account',
            'resourceId': targetAccountId
        }
    }
    functionCfg = {
        'Runtime': 'python3.8',
        'Handler': 'lambda_function.lambda_handler',
        'Timeout': 180,
        'MemorySize': 128
    }
    codeZip = getTestCode('ApplyS3BPA')
    profile = Profile()
    lambdac = LambdaClient(profile)
    functionName = "UnitTestS3BPALambda"
    functionDescription = "UnitTest S3BPA Lambda"
    lambdaRoleName = 'aws-controltower-AuditAdministratorRole'
    roleArn = profile.getRoleArn(lambdaRoleName)
    lambdaArn = lambdac.declareFunctionArn(functionName, functionDescription, roleArn, functionCfg, codeZip)
    functionOut = lambdac.invokeFunctionJson(functionName, event)
    print(functionOut)



test_s3bpa_invoke('119399605612')
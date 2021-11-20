from lib.rdq import Profile
from lib.rdq.svciam import IamClient
from lib.rdq.svclambda import LambdaClient
import lib.rdq.policy as policy
from cmds.codeLoader import getTestCode
from lib.rdq.svcs3control import S3ControlClient
from lambdas.test.ApplyS3BPA.lambda_function import lambda_handler

def targetAccountId():
    return '119399605612'

def dispatchAccountId():
    return '746869318262'

def targetRoleName():
    return 'UnitTestTargetRole'


def setup_targetAccount():
    print("ACTION: Ensure credentials set to target application account")
    trustAccountId = dispatchAccountId()
    profile = Profile()
    iam = IamClient(profile)
    roleName = targetRoleName()
    roleDescription = 'Role for executing unit tests from {}'.format(trustAccountId)
    trustPolicy = policy.trustAccount(trustAccountId)
    roleArn = iam.declareRoleArn(roleName, roleDescription, trustPolicy)
    adminPolicy = iam.declareAwsPolicyArn('AdministratorAccess', '/')
    iam.declareManagedPoliciesForRole(roleName, [adminPolicy])
    print("Declared role {}".format(roleArn))
    print("Account {} can be used as target for {}".format(profile.accountId, trustAccountId))
    return profile.accountId


def test_s3bpa_direct():
    print("ACTION: Ensure credentials set to dispatching audit account")
    toAccountId = targetAccountId()
    roleName = targetRoleName()
    event = {
        'preview': True,
        'conformancePackName': 'UnitTest',
        'configRuleName': 's3-account-level-public-access-blocks-periodic',
        'target': {
            'awsAccountId': toAccountId,
            'awsRegion': 'ap-southeast-2',
            'roleName': roleName,
            'resourceType': 'AWS::::Account',
            'resourceId': toAccountId
        }
    }
    fromProfile = Profile()
    targetProfile = fromProfile.assumeRole(toAccountId, roleName, fromProfile.regionName, 'Prepare-S3BPA')
    s3c = S3ControlClient(targetProfile)
    s3c.declarePublicAccessBlock(toAccountId, False)
    response = lambda_handler(event, {})
    print(response)


def test_s3bpa_invoke(targetAccountId):
    event = {
        'preview': True,
        'conformancePackName': 'UnitTest',
        'configRuleName': 's3-account-level-public-access-blocks-periodic',
        'target': {
            'awsAccountId': targetAccountId,
            'awsRegion': 'ap-southeast-2',
            'roleName': 'aws-controltower-AdministratorExecutionRole',
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


# setup_targetAccount()
test_s3bpa_direct()
# test_s3bpa_invoke('119399605612')
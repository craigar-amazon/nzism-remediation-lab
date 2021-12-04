from lib.rdq import Profile
from lib.rdq.svciam import IamClient
from lib.rdq.svclambda import LambdaClient
import lib.rdq.policy as policy
import cmds.codeLoader as codeLoader
import cfg.installer as cfg

def targetAccountId():
    return '119399605612'

def dispatchAccountId():
    return '746869318262'

def targetRoleNameDirect():
    return 'UnitTestTargetRole'

def targetRoleNameCT():
    return 'aws-controltower-AdministratorExecutionRole'

def auditRoleNameCT():
    return 'aws-controltower-AuditAdministratorRole'

def show_reminder_targetApplication():
    print("ACTION: Ensure credentials set to target application account")

def show_reminder_dispatchingAudit():
    print("ACTION: Ensure credentials set to dispatching audit account")


def setup_targetAccount():
    trustAccountId = dispatchAccountId()
    profile = Profile()
    iam = IamClient(profile)
    roleName = targetRoleNameDirect()
    roleDescription = 'Role for executing unit tests from {}'.format(trustAccountId)
    trustPolicy = policy.trustAccount(trustAccountId)
    roleArn = iam.declareRoleArn(roleName, roleDescription, trustPolicy)
    adminPolicy = iam.declareAwsPolicyArn('AdministratorAccess', '/')
    iam.declareManagedPoliciesForRole(roleName, [adminPolicy])
    print("Declared role {}".format(roleArn))
    print("Account {} can be used as target for {}".format(profile.accountId, trustAccountId))
    return profile.accountId

def run_local(preview, configRuleName, resourceType, resourceId, setupFunction, lambdaFunction):
    profile = Profile()
    roleName = 'LOCAL'
    event = {
        'preview': preview,
        'conformancePackName': 'UnitTest',
        'configRuleName': configRuleName,
        'target': {
            'awsAccountId': profile.accountId,
            'awsRegion': 'ap-southeast-2',
            'roleName': roleName,
            'resourceType': resourceType,
            'resourceId': resourceId
        }
    }
    if setupFunction:
        setupFunction(profile, resourceId)
    if lambdaFunction:
        response = lambdaFunction(event, {})
    else:
        response = None
    return response

def run_direct(preview, configRuleName, resourceType, resourceId, setupFunction, lambdaFunction):
    toAccountId = targetAccountId()
    roleName = targetRoleNameDirect()
    event = {
        'preview': preview,
        'conformancePackName': 'UnitTest',
        'configRuleName': configRuleName,
        'target': {
            'awsAccountId': toAccountId,
            'awsRegion': 'ap-southeast-2',
            'roleName': roleName,
            'resourceType': resourceType,
            'resourceId': resourceId
        }
    }
    fromProfile = Profile()
    targetProfile = fromProfile.assumeRole(toAccountId, roleName, fromProfile.regionName, 'DirectTestPrepare')
    if setupFunction:
        setupFunction(targetProfile, resourceId)
    if lambdaFunction:
        response = lambdaFunction(event, {})
    else:
        response = None
    return response

def run_invoke(preview, configRuleName, resourceType, resourceId, setupFunction, codeFolder):
    toAccountId = targetAccountId()
    prepRoleName = targetRoleNameDirect()
    lambdaRoleName = auditRoleNameCT()
    targetRoleName = targetRoleNameCT()
    event = {
        'preview': preview,
        'conformancePackName': 'UnitTest',
        'configRuleName': configRuleName,
        'target': {
            'awsAccountId': toAccountId,
            'awsRegion': 'ap-southeast-2',
            'roleName': targetRoleName,
            'resourceType': resourceType,
            'resourceId': resourceId
        }
    }
    functionCfg = cfg.ruleFunctionCfg()
    codeZip = codeLoader.getTestCode(codeFolder)
    profile = Profile()
    lambdac = LambdaClient(profile)
    functionName = "UnitTest-{}".format(codeFolder)
    functionDescription = "UnitTest {} Lambda".format(codeFolder)
    roleArn = profile.getRoleArn(lambdaRoleName)
    lambdaArn = lambdac.declareFunctionArn(functionName, functionDescription, roleArn, functionCfg, codeZip)
    print("Unit Test Lambda Deployed: {}".format(lambdaArn))
    targetProfile = profile.assumeRole(toAccountId, prepRoleName, profile.regionName, 'InvokeTestPrepare')
    if setupFunction:
        setupFunction(targetProfile, resourceId)

    response = lambdac.invokeFunctionJson(functionName, event)
    return response

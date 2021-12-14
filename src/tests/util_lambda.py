from lib.base import Tags
from lib.rdq import Profile
from lib.rdq.svciam import IamClient
from lib.rdq.svclambda import LambdaClient
import lib.rdq.policy as policy
import cmds.codeLoader as codeLoader
import cfg.core as cfgCore

def targetAccountId():
    return '119399605612'

def targetAccountName():
    return 'Application-1'

def targetAccountEmail():
    return 'craigar+ctapp1@amazon.com'

def dispatchAccountId():
    return '746869318262'

def targetRoleNameDirect():
    return 'UnitTestTargetRole'

def conformancePackName():
    return 'UnitTestConformancePack'

def manualTagName():
    return 'ManualRemediation'

def autoResourceTags():
    return {
        'AutoDeployed': 'True',
        'AutoDeploymentReason': 'NZISM Conformance'
    }

def stackNamePattern():
    return "NZISM-AutoDeployed-{}"

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

# {
#     'action': 'remediate',
#     'preview': True,
#     'conformancePackName': 'NZISM',
#     'configRuleName': 's3-account-level-public-access-blocks-periodic',
#     'manualTagName': 'ManualRemediation',
#     'autoResourceTags': {
#         'AutoDeployed': 'True',
#         'AutoDeploymentReason': 'NZISM Conformance',
#         'NZISM': 'CID:2022'
#     },
#     'stackNamePattern': 'NZISM-AutoDeployed-{}',
#     'deploymentMethod': {},
#     'target': {
#         'awsAccountId': '119399605612',
#         'awsAccountName': 'Application-1',
#         'awsAccountEmail': 'craigar+ctapp1@amazon.com',
#         'awsRegion': 'ap-southeast-2',
#         'roleName': 'aws-controltower-AdministratorExecutionRole',
#         'resourceType': 'AWS::::Account',
#         'resourceId': '119399605612'
#     }
# }

def run_local(preview, configRuleName, resourceType, resourceId, action, deploymentMethod, setupFunction, lambdaFunction):
    profile = Profile()
    roleName = 'LOCAL'
    event = {
        'action': action,
        'preview': preview,
        'conformancePackName': conformancePackName(),
        'configRuleName': configRuleName,
        'manualTagName': manualTagName(),
        'autoResourceTags': autoResourceTags(),
        'stackNamePattern': stackNamePattern(),
        'deploymentMethod': deploymentMethod,
        'target': {
            'awsAccountId': profile.accountId,
            'awsAccountName': targetAccountName(),
            'awsAccountEmail': targetAccountEmail(),
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

def run_direct(preview, configRuleName, resourceType, resourceId, action, deploymentMethod, setupFunction, lambdaFunction):
    toAccountId = targetAccountId()
    roleName = targetRoleNameDirect()
    event = {
        'action': action,
        'preview': preview,
        'conformancePackName': conformancePackName(),
        'configRuleName': configRuleName,
        'manualTagName': manualTagName(),
        'autoResourceTags': autoResourceTags(),
        'stackNamePattern': stackNamePattern(),
        'deploymentMethod': deploymentMethod,
        'target': {
            'awsAccountId': toAccountId,
            'awsAccountName': targetAccountName(),
            'awsAccountEmail': targetAccountEmail(),
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

def run_invoke(preview, configRuleName, resourceType, resourceId, action, deploymentMethod, setupFunction, codeFolder):
    toAccountId = targetAccountId()
    prepRoleName = targetRoleNameDirect()
    lambdaRoleName = auditRoleNameCT()
    targetRoleName = targetRoleNameCT()
    event = {
        'action': action,
        'preview': preview,
        'conformancePackName': conformancePackName(),
        'configRuleName': configRuleName,
        'manualTagName': manualTagName(),
        'autoResourceTags': autoResourceTags(),
        'stackNamePattern': stackNamePattern(),
        'deploymentMethod': deploymentMethod,
        'target': {
            'awsAccountId': toAccountId,
            'awsAccountName': targetAccountName(),
            'awsAccountEmail': targetAccountEmail(),
            'awsRegion': 'ap-southeast-2',
            'roleName': targetRoleName,
            'resourceType': resourceType,
            'resourceId': resourceId
        }
    }
    functionCfg = cfgCore.ruleFunctionCfg(codeFolder)
    tagsRule = Tags(cfgCore.ruleResourceTags(), "ruleResourceTags")
    codeZip = codeLoader.getTestCode(codeFolder)
    profile = Profile()
    lambdac = LambdaClient(profile)
    functionName = "UnitTest-{}".format(codeFolder)
    functionDescription = "UnitTest {} Lambda".format(codeFolder)
    roleArn = profile.getRoleArn(lambdaRoleName)
    lambdaArn = lambdac.declareFunctionArn(functionName, functionDescription, roleArn, functionCfg, codeZip, tagsRule)
    print("Unit Test Lambda Deployed: {}".format(lambdaArn))
    targetProfile = profile.assumeRole(toAccountId, prepRoleName, profile.regionName, 'InvokeTestPrepare')
    if setupFunction:
        setupFunction(targetProfile, resourceId)

    response = lambdac.invokeFunctionJson(functionName, event)
    return response

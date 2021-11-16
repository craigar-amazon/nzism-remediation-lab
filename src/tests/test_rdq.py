from lib.rdq import Profile
from lib.rdq.svciam import IamClient
from lib.rdq.svclambda import LambdaClient
from lib.rdq.svckms import KmsClient
import lib.rdq.policy as policy
from cmds.codeLoader import getTestCode

def test_lambda_policy():
    iam = IamClient(Profile())
    lambdaPolicyArn = iam.declareAwsPolicyArn(policy.awsLambdaBasicExecution())
    assert lambdaPolicyArn == 'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'


def test_policy_declare():
    profile = Profile()
    iam = IamClient(profile)
    policyName = 'NZQueueReader'
    expectedPolicyArn = profile.getGlobalAccountArn('iam', "policy/{}".format(policyName))
    policyDescription = 'Process compliance change queue' 
    sqsArn = profile.getRegionAccountArn("sqs", "ComplianceChangeQueue")
    policyMap = policy.permissions([policy.allowConsumeSQS(sqsArn)])
    arn1 = iam.declareCustomerPolicyArn(policyName, policyDescription, policyMap)
    assert arn1 == expectedPolicyArn
    arn2 = iam.declareCustomerPolicyArn(policyName, policyDescription, policyMap)
    assert arn2 == expectedPolicyArn
    sqsArn1 = profile.getRegionAccountArn("sqs", "ComplianceChangeQueue1")
    policyMap1 = policy.permissions([policy.allowConsumeSQS(sqsArn1)])
    arn3 = iam.declareCustomerPolicyArn(policyName, policyDescription, policyMap1)
    assert arn3 == expectedPolicyArn
    arn4 = iam.declareCustomerPolicyArn(policyName, policyDescription, policyMap1)
    assert arn4 == expectedPolicyArn
    sqsArn2 = profile.getRegionAccountArn("sqs", "ComplianceChangeQueue2")
    policyMap2 = policy.permissions([policy.allowConsumeSQS(sqsArn2)])
    arn5 = iam.declareCustomerPolicyArn(policyName, policyDescription, policyMap2)
    assert arn5 == expectedPolicyArn
    iam.deleteCustomerPolicy(arn5)
    assert not iam.getCustomerPolicy(policyName)

def test_role_declare():
    profile = Profile()
    iam = IamClient(profile)
    roleName = 'TestComplianceChangeConsumerLambdaRole'
    expectedRoleArn = profile.getGlobalAccountArn('iam', "role/{}".format(roleName))
    roleDescription = 'Compliance change queue lambda consumer role'
    lambdaTrustPolicy = policy.trustLambda()
    trustPolicy2 = policy.trustEventBridge()
    roleDescription2 = 'Compliance change SQS queue Lambda consumer role'
    roleArn1 = iam.declareRoleArn(roleName, roleDescription, lambdaTrustPolicy)
    assert roleArn1 == expectedRoleArn
    roleArn2 = iam.declareRoleArn(roleName, roleDescription, lambdaTrustPolicy)
    assert roleArn2 == expectedRoleArn
    roleArn3 = iam.declareRoleArn(roleName, roleDescription2, trustPolicy2)
    assert roleArn3 == expectedRoleArn
    iam.deleteRole(roleName)
    assert not iam.getRole(roleName)


def test_role_build():
    profile = Profile()
    iam = IamClient(profile)
    lambdaPolicyName = policy.awsLambdaBasicExecution()
    roleName = 'ComplianceChangeConsumerLambdaRole'
    expectedRoleArn = profile.getGlobalAccountArn('iam', "role/{}".format(roleName))
    roleDescription = 'Compliance change queue lambda consumer role'
    lambdaPolicyArn = iam.declareAwsPolicyArn(lambdaPolicyName)
    lambdaPolicyArn1 = iam.declareAwsPolicyArn('AWSLambdaSQSQueueExecutionRole')
    lambdaTrustPolicy = policy.trustLambda()
    roleArn1 = iam.declareRoleArn(roleName, roleDescription, lambdaTrustPolicy)
    assert roleArn1 == expectedRoleArn
    iam.declareManagedPoliciesForRole(roleName, [lambdaPolicyArn])
    iam.declareManagedPoliciesForRole(roleName, [lambdaPolicyArn, lambdaPolicyArn1])
    iam.declareManagedPoliciesForRole(roleName, [lambdaPolicyArn1])
    sqsArn1 = profile.getRegionAccountArn("sqs", "ComplianceChangeQueue1")
    sqsArn2 = profile.getRegionAccountArn("sqs", "ComplianceChangeQueue2")
    policyMapSQS1 = policy.permissions([policy.allowConsumeSQS(sqsArn1)])
    policyMapSQS2 = policy.permissions([policy.allowConsumeSQS(sqsArn2)])
    iam.declareInlinePoliciesForRole(roleName, {'QueueA': policyMapSQS1})
    iam.declareInlinePoliciesForRole(roleName, {'QueueA': policyMapSQS1})
    iam.declareInlinePoliciesForRole(roleName, {'QueueA': policyMapSQS2, 'QueueB': policyMapSQS1})
    iam.declareInlinePoliciesForRole(roleName, {'QueueB': policyMapSQS2})
    iam.deleteRole(roleName)
    assert not iam.getRole(roleName)

def test_lambda():
    codeZip = getTestCode('Echo')
    profile = Profile()
    iamc = IamClient(profile)
    lambdac = LambdaClient(profile)
    lambdaPolicyArn = iamc.declareAwsPolicyArn(policy.awsLambdaBasicExecution())
    lambdaTrustPolicy = policy.trustLambda()
    roleDescription = 'UnitTest1 Lambda Role'
    roleName = 'UnitTest1LambdaRole'
    functionName = "UnitTest1Lambda"
    functionDescription = "UnitTest1 Lambda" 
    functionCfg = {
        'Runtime': 'python3.8',
        'Handler': 'lambda_function.lambda_handler',
        'Timeout': 180,
        'MemorySize': 128
    }
    iamc.deleteRole(roleName)
    lambdac.deleteFunction(functionName)
    expectedLambdaArn = profile.getRegionAccountArn('lambda', "function:{}".format(functionName))
    roleArn = iamc.declareRoleArn(roleName, roleDescription, lambdaTrustPolicy)
    iamc.declareManagedPoliciesForRole(roleName, [lambdaPolicyArn])
    lambdaArn = lambdac.declareFunctionArn(functionName, functionDescription, roleArn, functionCfg, codeZip)
    assert lambdaArn == expectedLambdaArn
    functionDescriptionDelta1 = functionDescription + " Delta1"
    lambdaArn1 = lambdac.declareFunctionArn(functionName, functionDescriptionDelta1, roleArn, functionCfg, codeZip)
    assert lambdaArn1 == expectedLambdaArn
    codeZipDelta1 = getTestCode('SimpleCredentialCheck')
    lambdaArn2 = lambdac.declareFunctionArn(functionName, functionDescriptionDelta1, roleArn, functionCfg, codeZipDelta1)
    assert lambdaArn2 == expectedLambdaArn
    functionIn = {
        'source': "unit-test"
    }
    functionOut = lambdac.invokeFunctionJson(functionName, functionIn)
    assert functionOut
    assert 'StatusCode' in functionOut
    assert functionOut['StatusCode'] == 200

    lambdac.deleteFunction(functionName)
    iamc.deleteRole(roleName)

def test_cmk():
    sqsCmkDescription = "Encryption for SQS queued events"
    sqsCmkAlias = "queued_events"
    profile = Profile()
    storageServiceNS = policy.serviceNamespaceSQS()
    producerServiceP = policy.principalEventBridge()
    cmkStatements = [ policy.allowCMKForServiceProducer(profile, storageServiceNS, producerServiceP) ]
    kmsc = KmsClient(profile)
#    kmsc.deleteCMK(sqsCmkAlias)
    cmkarn1 = kmsc.declareCMKArn(sqsCmkDescription, sqsCmkAlias, cmkStatements)
    assert cmkarn1

# test_lambda_policy()
# test_policy_declare()
# test_role_declare()
# test_role_build()
# test_lambda()
test_cmk()
import unittest
from lib.rdq import Profile
from lib.rdq.svciam import IamClient
from lib.rdq.svcorg import OrganizationClient
from lib.rdq.svclambda import LambdaClient
from lib.rdq.svckms import KmsClient
from lib.rdq.svcsqs import SQSClient
from lib.rdq.svceventbridge import EventBridgeClient
import lib.rdq.policy as policy
from cmds.codeLoader import getCoreCode, getTestCode

def setup_assume_role(callingAccountId):
    profile = Profile()
    iam = IamClient(profile)
    roleName = 'UnitTest1Assume'
    roleDescription = "Account {} can assume this role".format(callingAccountId)
    trustPolicy = policy.trustAccount(callingAccountId)
    iam.declareRoleArn(roleName, roleDescription, trustPolicy)

def test_assume_role(targetAccountId):
    profile = Profile()
    roleName = 'UnitTest1Assume'
    newProfile = profile.assumeRole(targetAccountId, roleName, profile.regionName, "TestSession")


class TestRdq(unittest.TestCase):
    def test_lambda_policy(self):
        iam = IamClient(Profile())
        lambdaPolicyArn = iam.declareAwsPolicyArn(policy.awsLambdaBasicExecution())
        assert lambdaPolicyArn == 'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'

    def test_policy_declare(self):
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

    def test_role_declare(self):
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

    def test_role_build(self):
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


    def test_lambda(self):
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

    def test_cmk(self):
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

    def test_eventBus(self):
        profile = Profile()
        ebc = EventBridgeClient(profile)
        kmsc = KmsClient(profile)
        sqsc = SQSClient(profile)
        orgc = OrganizationClient(profile)

        sqsCmkDescription = "Encryption for SQS queued events"
        sqsCmkAlias = "queued_events"
        storageServiceNS = policy.serviceNamespaceSQS()
        producerServiceP = policy.principalEventBridge()
        cmkStatements = [ policy.allowCMKForServiceProducer(profile, storageServiceNS, producerServiceP) ]
        cmkarn = kmsc.declareCMKArn(sqsCmkDescription, sqsCmkAlias, cmkStatements)
        queueName = 'UnitTestQueue1'
        eventBusName = 'UnitTestBus1'
        ruleName = 'ComplianceChange'
        ruleDescription = "Config Rule Compliance Change"
        eventPattern = {
            'source': ["aws.config"],
            'detail-type': ["Config Rules Compliance Change"]
        }
        maxAgeSecs = 12 * 3600
        ebArnExpected = profile.getRegionAccountArn('events', "event-bus/{}".format(eventBusName))
        ruleArnExpected = profile.getRegionAccountArn('events', "rule/{}/{}".format(eventBusName, ruleName))
        orgId = orgc.getOrganizationId()
        ebArn = ebc.declareEventBusArn(eventBusName)
        self.assertEqual(ebArn, ebArnExpected)
        ruleArn = ebc.declareEventBusRuleArn(eventBusName, ruleName, ruleDescription, eventPattern)
        self.assertEqual(ruleArn, ruleArnExpected)
        sqsStatements = [ policy.allowSQSForServiceProducer(profile, queueName, producerServiceP, ruleArn) ]
        sqsVisibilityTimeoutSecs = 15 * 60
        sqsArn = sqsc.declareQueueArn(queueName, cmkarn, sqsStatements, sqsVisibilityTimeoutSecs)
        sqsArnExpected = profile.getRegionAccountArn('sqs', queueName)
        self.assertEqual(sqsArn, sqsArnExpected)
        ebc.declareEventBusTarget(eventBusName, ruleName, queueName, sqsArn, maxAgeSecs)
        ebc.declareEventBusPublishPermissionForOrganization(eventBusName, orgId)

        ebArn1 = ebc.declareEventBusArn(eventBusName)
        self.assertEqual(ebArn, ebArn1, "Idempotent EventBus")
        sqsArn1 = sqsc.declareQueueArn(queueName, cmkarn, sqsStatements, (sqsVisibilityTimeoutSecs + 1))
        self.assertEqual(sqsArn, sqsArn1, "Idempotent Queue")
        ebc.declareEventBusTarget(eventBusName, ruleName, queueName, sqsArn, (maxAgeSecs + 1))

        sqsc.deleteQueue(queueName)
        ebc.deleteEventBus(eventBusName)

    def test_dispatcher(self):
        cpack = 'NZISM'
        codeZip = getCoreCode('ComplianceDispatcher')
        profile = Profile()
        iamc = IamClient(profile)
        orgc = OrganizationClient(profile)
        kmsc = KmsClient(profile)
        lambdac = LambdaClient(profile)
        ebc = EventBridgeClient(profile)
        sqsc = SQSClient(profile)

        sqsVisibilityTimeoutSecs = 15 * 60
        ebTargetMaxAgeSecs = 12 * 3600
        lambdaTimeoutSecs = 180
        sqsPollCfg = {
            'BatchSize': 5,
            'MaximumBatchingWindowInSeconds': 0
        }

        sqsCmkDescription = "Encryption for SQS queued events"
        sqsCmkAlias = "queued_events"
        eventBusName = '{}-AutoRemediation'.format(cpack)
        queueName = '{}-ComplianceChangeQueue'.format(cpack)
        ruleName = 'ComplianceChange'
        ruleDescription = "Config Rule Compliance Change"
        eventPattern = {
            'source': ["aws.config"],
            'detail-type': ["Config Rules Compliance Change"]
        }
        lambdaRoleDescription = "{} Compliance Dispatcher Lambda Role".format(cpack)
        lambdaRoleName = '{}-ComplianceDispatcher-LambdaRole'.format(cpack)
        functionName = '{}-ComplianceDispatcher'.format(cpack)
        functionDescription = '{} Compliance Dispatcher Lambda'.format(cpack)
        functionCfg = {
            'Runtime': 'python3.8',
            'Handler': 'lambda_function.lambda_handler',
            'Timeout': lambdaTimeoutSecs,
            'MemorySize': 128
        }

        orgId = orgc.getOrganizationId()
        ebc.declareEventBusArn(eventBusName)
        ruleArn = ebc.declareEventBusRuleArn(eventBusName, ruleName, ruleDescription, eventPattern)

        cmkStatements = [ policy.allowCMKForServiceProducer(profile, policy.serviceNamespaceSQS(), policy.principalEventBridge()) ]
        cmkarn = kmsc.declareCMKArn(sqsCmkDescription, sqsCmkAlias, cmkStatements)
        sqsStatements = [ policy.allowSQSForServiceProducer(profile, queueName, policy.principalEventBridge(), ruleArn) ]
        sqsArn = sqsc.declareQueueArn(queueName, cmkarn, sqsStatements, sqsVisibilityTimeoutSecs)
        ebc.declareEventBusTarget(eventBusName, ruleName, queueName, sqsArn, ebTargetMaxAgeSecs)
        ebc.declareEventBusPublishPermissionForOrganization(eventBusName, orgId)

        lambdaPolicyArn = iamc.declareAwsPolicyArn(policy.awsLambdaBasicExecution())
        roleArn = iamc.declareRoleArn(lambdaRoleName, lambdaRoleDescription, policy.trustLambda())
        iamc.declareManagedPoliciesForRole(lambdaRoleName, [lambdaPolicyArn])
        policyMapSQS = policy.permissions([policy.allowConsumeSQS(sqsArn)])
        iamc.declareInlinePoliciesForRole(lambdaRoleName, {'ComplianceChangeEventQueue': policyMapSQS})
        lambdaArn = lambdac.declareFunctionArn(functionName, functionDescription, roleArn, functionCfg, codeZip)
        lambdac.declareEventSourceMappingUUID(functionName, sqsArn, sqsPollCfg)

        lambdac.deleteEventSourceMapping(functionName, sqsArn)
        lambdac.deleteFunction(functionName)
        iamc.deleteRole(lambdaRoleName)
        sqsc.deleteQueue(queueName)
        ebc.deleteEventBus(eventBusName)



if __name__ == '__main__':
    loader = unittest.TestLoader()
    loader.testMethodPrefix = "test_dispatcher"
    unittest.main(warnings='default', testLoader = loader)
    # setup_assume_role('746869318262')
    # test_assume_role('119399605612')
    pass

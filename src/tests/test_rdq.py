import unittest
from lib.base import initLogging, Tags
from lib.rdq import Profile
from lib.rdq.svciam import IamClient
from lib.rdq.svcorg import OrganizationClient
from lib.rdq.svclambda import LambdaClient
from lib.rdq.svckms import KmsClient
from lib.rdq.svcsqs import SQSClient
from lib.rdq.svceventbridge import EventBridgeClient
from lib.rdq.svccfn import CfnClient
import lib.rdq.policy as policy
import lib.lambdas.discover as discover

import lib.cfn as cfn
import lib.cfn.iam as iam
import lib.cfn.eventbridge as eb
import lib.cfn.kms as kms
import lib.cfn.cloudwatchlogs as cwl


import cfg.installer as cfgInstaller
import cmds.codeLoader as codeLoader

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
        tags = Tags({'Application': 'NZISM Auto Remediation'})
        tagsB = Tags({'Phase': 'B'})
        roleName = 'TestComplianceChangeConsumerLambdaRole'
        expectedRoleArn = profile.getGlobalAccountArn('iam', "role/{}".format(roleName))
        roleDescription = 'Compliance change queue lambda consumer role'
        lambdaTrustPolicy = policy.trustLambda()
        trustPolicy2 = policy.trustEventBridge()
        roleDescription2 = 'Compliance change SQS queue Lambda consumer role'
        roleArn1 = iam.declareRoleArn(roleName, roleDescription, lambdaTrustPolicy, tags)
        assert roleArn1 == expectedRoleArn
        roleArn2 = iam.declareRoleArn(roleName, roleDescription, lambdaTrustPolicy, tags)
        assert roleArn2 == expectedRoleArn
        roleArn3 = iam.declareRoleArn(roleName, roleDescription2, trustPolicy2, tagsB)
        assert roleArn3 == expectedRoleArn
        iam.deleteRole(roleName)
        assert not iam.getRole(roleName)

    def test_role_build(self):
        profile = Profile()
        iam = IamClient(profile)
        tags = Tags({'Application': 'NZISM Auto Remediation'})
        lambdaPolicyName = policy.awsLambdaBasicExecution()
        roleName = 'ComplianceChangeConsumerLambdaRole'
        expectedRoleArn = profile.getGlobalAccountArn('iam', "role/{}".format(roleName))
        roleDescription = 'Compliance change queue lambda consumer role'
        lambdaPolicyArn = iam.declareAwsPolicyArn(lambdaPolicyName)
        lambdaPolicyArn1 = iam.declareAwsPolicyArn('AWSLambdaSQSQueueExecutionRole')
        lambdaTrustPolicy = policy.trustLambda()
        roleArn1 = iam.declareRoleArn(roleName, roleDescription, lambdaTrustPolicy, tags)
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
        codeZip = codeLoader.getTestCode('Echo')
        profile = Profile()
        iamc = IamClient(profile)
        lambdac = LambdaClient(profile)
        tags = Tags({'Application': 'NZISM Auto Remediation'})
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
        roleArn = iamc.declareRoleArn(roleName, roleDescription, lambdaTrustPolicy, tags)
        iamc.declareManagedPoliciesForRole(roleName, [lambdaPolicyArn])
        lambdaArn = lambdac.declareFunctionArn(functionName, functionDescription, roleArn, functionCfg, codeZip, tags)
        assert lambdaArn == expectedLambdaArn
        functionDescriptionDelta1 = functionDescription + " Delta1"
        lambdaArn1 = lambdac.declareFunctionArn(functionName, functionDescriptionDelta1, roleArn, functionCfg, codeZip, tags)
        assert lambdaArn1 == expectedLambdaArn
        codeZipDelta1 = codeLoader.getTestCode('SimpleCredentialCheck')
        lambdaArn2 = lambdac.declareFunctionArn(functionName, functionDescriptionDelta1, roleArn, functionCfg, codeZipDelta1, tags)
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
        tags = Tags({'Application': 'NZISM Auto Remediation'})
        storageServiceNS = policy.serviceNamespaceSQS()
        producerServiceP = policy.principalEventBridge()
        cmkStatements = [ policy.allowCMKForServiceProducer(profile, storageServiceNS, producerServiceP) ]
        kmsc = KmsClient(profile)
    #    kmsc.deleteCMK(sqsCmkAlias)
        cmkarn1 = kmsc.declareCMKArn(sqsCmkDescription, sqsCmkAlias, cmkStatements, tags)
        assert cmkarn1

    def test_eventBus(self):
        profile = Profile()
        ebc = EventBridgeClient(profile)
        kmsc = KmsClient(profile)
        sqsc = SQSClient(profile)
        orgc = OrganizationClient(profile)

        tags = Tags({'Application': 'NZISM Auto Remediation'})
        tagsB = Tags({'Phase': 'B'})
        sqsCmkDescription = "Encryption for SQS queued events"
        sqsCmkAlias = "queued_events"
        storageServiceNS = policy.serviceNamespaceSQS()
        producerServiceP = policy.principalEventBridge()
        cmkStatements = [ policy.allowCMKForServiceProducer(profile, storageServiceNS, producerServiceP) ]
        cmkarn = kmsc.declareCMKArn(sqsCmkDescription, sqsCmkAlias, cmkStatements, tags)
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
        ebArn = ebc.declareEventBusArn(eventBusName, tags)
        self.assertEqual(ebArn, ebArnExpected)
        ruleArn = ebc.declareEventBusRuleArn(eventBusName, ruleName, ruleDescription, eventPattern, tags)
        self.assertEqual(ruleArn, ruleArnExpected)
        sqsStatements = [ policy.allowSQSForServiceProducer(profile, queueName, producerServiceP, ruleArn) ]
        sqsVisibilityTimeoutSecs = 15 * 60
        sqsArn = sqsc.declareQueueArn(queueName, cmkarn, sqsStatements, sqsVisibilityTimeoutSecs, tags)
        sqsArnExpected = profile.getRegionAccountArn('sqs', queueName)
        self.assertEqual(sqsArn, sqsArnExpected)
        ebc.declareEventBusTarget(eventBusName, ruleName, queueName, sqsArn, maxAgeSecs)
        ebc.declareEventBusPublishPermissionForOrganization(eventBusName, orgId)

        ebArn1 = ebc.declareEventBusArn(eventBusName, tags)
        self.assertEqual(ebArn, ebArn1, "Idempotent EventBus")
        ruleArn1 = ebc.declareEventBusRuleArn(eventBusName, ruleName, ruleDescription, eventPattern, tags)
        self.assertEqual(ruleArn, ruleArn1, "Idempotent EventBus Rule")
        sqsArn1 = sqsc.declareQueueArn(queueName, cmkarn, sqsStatements, (sqsVisibilityTimeoutSecs + 1), tagsB)
        self.assertEqual(sqsArn, sqsArn1, "Idempotent Queue")
        ebc.declareEventBusTarget(eventBusName, ruleName, queueName, sqsArn, maxAgeSecs)
        ebc.declareEventBusTarget(eventBusName, ruleName, queueName, sqsArn, (maxAgeSecs + 1))

        print("Done")

        sqsc.deleteQueue(queueName)
        ebc.deleteEventBus(eventBusName)

    def test_dispatcher(self):
        profile = Profile()
        iamc = IamClient(profile)
        orgc = OrganizationClient(profile)
        kmsc = KmsClient(profile)
        lambdac = LambdaClient(profile)
        ebc = EventBridgeClient(profile)
        sqsc = SQSClient(profile)

        queueCfg = cfgInstaller.coreQueueCfg()
        sqsVisibilityTimeoutSecs = queueCfg['SqsVisibilityTimeoutSecs']
        sqsPollCfg = queueCfg['SqsPollCfg']

        ebCfg = cfgInstaller.coreEventBusCfg()
        ebTargetMaxAgeSecs = ebCfg['RuleTargetMaxAgeSecs']

        tagsCore = Tags(cfgInstaller.coreResourceTags(), "coreResourceTags")
        tagsCore.putAll(Lifecycle="Unit Test")
        tagsRule = Tags(cfgInstaller.ruleResourceTags(), "ruleResourceTags")
        tagsRule.putAll(Lifecycle="Development")

        sqsCmkDescription = "Encryption for SQS queued events"
        sqsCmkAlias = "queued_events"
        eventBusName = cfgInstaller.coreResourceName('AutoRemediation')
        queueName = cfgInstaller.coreResourceName('ComplianceChangeQueue')
        ruleName = 'ComplianceChange'
        ruleDescription = "Config Rule Compliance Change"
        eventPattern = {
            'source': ["aws.config"],
            'detail-type': ["Config Rules Compliance Change"]
        }
        codeFolder = 'ComplianceDispatcher'
        codeZip = codeLoader.getCoreCode(codeFolder)
        lambdaRoleDescription = "Compliance Dispatcher Lambda Role"
        lambdaRoleName = cfgInstaller.coreResourceName('ComplianceDispatcher-LambdaRole')
        functionName = cfgInstaller.coreFunctionName(codeFolder)
        functionDescription = 'Compliance Dispatcher Lambda'
        functionCfg = cfgInstaller.coreFunctionCfg()

        isLandingZoneDiscoveryEnabled = discover.isLandingZoneDiscoveryEnabled()
        landingZoneConfig = discover.discoverLandingZone(profile)

        ebc.declareEventBusArn(eventBusName, tagsCore)
        ruleArn = ebc.declareEventBusRuleArn(eventBusName, ruleName, ruleDescription, eventPattern, tagsCore)

        cmkStatements = [ policy.allowCMKForServiceProducer(profile, policy.serviceNamespaceSQS(), policy.principalEventBridge()) ]
        cmkarn = kmsc.declareCMKArn(sqsCmkDescription, sqsCmkAlias, cmkStatements, tagsCore)
        sqsStatements = [ policy.allowSQSForServiceProducer(profile, queueName, policy.principalEventBridge(), ruleArn) ]
        sqsArn = sqsc.declareQueueArn(queueName, cmkarn, sqsStatements, sqsVisibilityTimeoutSecs, tagsCore)
        ebc.declareEventBusTarget(eventBusName, ruleName, queueName, sqsArn, ebTargetMaxAgeSecs)
        if landingZoneConfig:
            orgId = orgc.getOrganizationId()
            ebc.declareEventBusPublishPermissionForOrganization(eventBusName, orgId)
        else:
            ebc.declareEventBusPublishPermissionForAccount(eventBusName, profile.accountId)
        lambdaPolicyArn = iamc.declareAwsPolicyArn(policy.awsLambdaBasicExecution())
        roleArn = iamc.declareRoleArn(lambdaRoleName, lambdaRoleDescription, policy.trustLambda(), tagsCore)
        iamc.declareManagedPoliciesForRole(lambdaRoleName, [lambdaPolicyArn])
        policyMapSQS = policy.permissions([policy.allowConsumeSQS(sqsArn), policy.allowDecryptCMK(cmkarn)])
        remediationLambdaNamePattern = "function:{}".format(cfgInstaller.ruleFunctionName("*"))
        remediationLambdaArn = profile.getRegionAccountArn('lambda', remediationLambdaNamePattern)
        policyMapInvoke = policy.permissions([policy.allowInvokeLambda(remediationLambdaArn)])
        inlinePolicyMap = {"ConsumeQueue": policyMapSQS, "InvokeRemediations": policyMapInvoke}
        if isLandingZoneDiscoveryEnabled:
            inlinePolicyMap['DiscoverRoles'] = policy.permissions([policy.allowDescribeIam("*")])
        iamc.declareInlinePoliciesForRole(lambdaRoleName, inlinePolicyMap)
        lambdaArn = lambdac.declareFunctionArn(functionName, functionDescription, roleArn, functionCfg, codeZip, tagsCore)
        lambdac.declareEventSourceMappingUUID(functionName, sqsArn, sqsPollCfg)

        ruleFolders = codeLoader.getAvailableRules()
        self.assertIsNotNone(landingZoneConfig) # Add support for single accounts
        ruleRoleArn = landingZoneConfig['AuditRoleArn']
        for ruleFolder in ruleFolders:
            rZip = codeLoader.getRuleCode(ruleFolder)
            rFunctionName = cfgInstaller.ruleFunctionName(ruleFolder)
            rFunctionDescription = '{} Auto Remediation Lambda'.format(ruleFolder)
            rFunctionCfg = cfgInstaller.ruleFunctionCfg(ruleFolder)
            rLambdaArn = lambdac.declareFunctionArn(rFunctionName, rFunctionDescription, ruleRoleArn, rFunctionCfg, rZip, tagsRule)

        print("Done")

        for ruleFolder in ruleFolders:
            rFunctionName = cfgInstaller.ruleFunctionName(ruleFolder)
            lambdac.deleteFunction(rFunctionName)
        lambdac.deleteEventSourceMapping(functionName, sqsArn)
        lambdac.deleteFunction(functionName)
        iamc.deleteRole(lambdaRoleName)
        sqsc.deleteQueue(queueName)
        ebc.deleteEventBus(eventBusName)


    def test_stack_local(self):
        cmkAliasBaseName = 'cwlog'
        cmkDescription = "For use by CloudWatch Log Service"
        cmkSid = "cwl"
        stackName = "NZISM-AutoDeployed-CloudWatchLogs-CMK"
        stackDescription = "Creates CMK for encrypting CloudWatch Logs"
        stackMaxSecs = 300
        profile = Profile()
        task_regionName = profile.regionName
        task_accountId = profile.accountId
        task_autoResourceTags = Tags({'AutoDeployed': 'True', 'AutoDeploymentReason': 'NZISM Conformance' })

        cfnc = CfnClient(profile)
        cycle = 1
        for _cmk in ['rCMK', 'rCMK', 'rCMK1']:
            _keyAlias = 'rKeyAlias'
            regionName = task_regionName
            accountId = task_accountId
            principal = cwl.iamPrincipal(regionName)
            condition = iam.ArnLike(cwl.kmsEncryptionContextKey(), cwl.kmsEncryptionContextValue(regionName, accountId, "*"))
            actions = [kms.iamEncrypt, kms.iamDecrypt, kms.iamReEncrypt, kms.iamGenerateDataKey, kms.iamDescribe]
            allowCwl = iam.ResourceAllow(actions, principal, "*", condition, cmkSid)
            keyPolicy = kms.KeyPolicy(accountId, [allowCwl])
            resources = {}
            resources[_cmk] = kms.KMS_Key(cmkDescription, keyPolicy, task_autoResourceTags)
            resources[_keyAlias] = kms.KMS_Alias(cmkAliasBaseName, cfn.Ref(_cmk))
            template = cfn.Template(stackDescription, resources)
            stackId = cfnc.declareStack(stackName, template, task_autoResourceTags)
            optStack = cfnc.getCompletedStack(stackName, stackMaxSecs)
            self.assertTrue(len(optStack) > 0)
            cycle = cycle + 1

        cfnc.removeStack(stackName)


    def test_stackset(self):
        tagsCore = Tags(cfgInstaller.coreResourceTags(), "coreResourceTags")
        stackSetName = "UnitTest1StackSet"
        stackSetDescription = "UnitTest1 Stack Set"

        eventBusName = 'default'
        ruleName = 'UnitTest1Rule'
        ruleDescription = "Config Rule Compliance Change"
        targetId = "unittest1Target"
        inlinePolicyName = 'UnitTest1InlinePolicy'
        roleName = 'UnitTest1EventBusRole'
        roleDescription = 'UnitTest1 EventBus Target Role'
        arnTargetEventBus = "arn:aws:events:ap-southeast-2:746869318262:event-bus/NZISM-AutoRemediation"
        regions = ['ap-southeast-2']
        rootId = 'r-djii'
        ouId1 = 'ou-djii-q1v40guj'
        ouIdSec = 'ou-djii-yzvg6i7l'
        orgIds = [ ouId1, ouIdSec ]

        resourceMap = {}
        allowEventBusPutEvent = iam.Allow([eb.iamPutEvents], [arnTargetEventBus])
        policyDocument = iam.PolicyDocument([allowEventBusPutEvent])
        inlinePolicy = iam.InlinePolicy(inlinePolicyName, policyDocument)
        trustPolicy = iam.TrustPolicy(eb.iamPrincipal)
        resourceMap['rRole'] = iam.IAM_Role(roleName, roleDescription, trustPolicy, None, [inlinePolicy])

        ruleTarget = eb.Target(targetId, arnTargetEventBus, cfn.Arn('rRole'))
        eventPattern = eb.EventPattern_ConfigComplianceChange()
        resourceMap['rEventRule'] = eb.rRule(eventBusName, ruleName, eventPattern, [ruleTarget])
        templateMap = cfn.Template(stackSetDescription, resourceMap)
        profile = Profile()
        cfnc = CfnClient(profile)
        cfnc.removeStackSet(stackSetName, orgIds, regions)
        ss0 = cfnc.declareStackSet(stackSetName, templateMap, stackSetDescription, tagsCore, orgIds, regions)
        self.assertTrue(len(ss0) == 2)
        ss1 = cfnc.declareStackSet(stackSetName, templateMap, stackSetDescription, tagsCore, orgIds, regions)
        self.assertTrue(len(ss1) == 2)
        self.assertIsNone(ss1['OperationId'])
        ss2 = cfnc.declareStackSet(stackSetName, templateMap, (stackSetDescription + ".1"), tagsCore, orgIds, regions)
        self.assertTrue(len(ss2) == 2)
        op2 = ss2['OperationId']
        summary2 = cfnc.getStackSetOperation(stackSetName, op2)
        self.assertTrue(len(summary2) > 0)
        cfnc.isRunningStackSetOperations(stackSetName)
        print("Done")
        cfnc.removeStackSet(stackSetName, orgIds, regions)



if __name__ == '__main__':
    initLogging(None, 'INFO')
    loader = unittest.TestLoader()
    loader.testMethodPrefix = "test_stack_local"
    unittest.main(warnings='default', testLoader = loader)
    # setup_assume_role('746869318262')
    # test_assume_role('119399605612')
    pass

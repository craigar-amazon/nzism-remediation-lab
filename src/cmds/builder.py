from lib.base import Tags, ConfigError

from lib.rdq import Profile
from lib.rdq.svciam import IamClient, RoleDescriptor
from lib.rdq.svcorg import OrganizationDescriptor
from lib.rdq.svckms import KmsClient
from lib.rdq.svceventbridge import EventBridgeClient
from lib.rdq.svcsqs import SqsClient
from lib.rdq.svclambda import LambdaClient

import lib.rdq.policy as policy


from lib.lambdas.discovery import LandingZoneDiscovery

import cfg.core
import cmds.codeLoader as codeLoader

def getValue(map, mapPath, key):
    if map is None: raise ConfigError("{} is undefined".format(mapPath))
    if len(map) == 0: raise ConfigError("{} is empty".format(mapPath))
    value = map.get(key, None)
    if value is None: raise ConfigError("{} in {} is undefined", key, mapPath)
    return value

class Clients:
    def __init__(self, args, profile :Profile):
        self.iam = IamClient(profile)
        self.kms = KmsClient(profile)
        self.eb = EventBridgeClient(profile)
        self.sqs = SqsClient(profile)
        self.lambdafun = LambdaClient(profile)


class BaseState:
    def __init__(self, args, profile :Profile):
        self.args = args
        self.profile = profile
        self.tagsCore = Tags(cfg.core.coreResourceTags(), context="cfg.core.coreResourceTags")
        self.eventBusName = cfg.core.coreResourceName('AutoRemediationEventBus')
        self.complianceRuleName = cfg.core.coreResourceName('ComplianceChangeRule')
        self.sqsCmkAlias = cfg.core.coreQueueCMKAlias()
        self.queueName = cfg.core.coreResourceName('ComplianceChangeQueue')
        self.dispatchLambdaRoleName = cfg.core.coreResourceName('ComplianceDispatcher-LambdaRole')
        self.dispatchLambdaCodeName = 'ComplianceDispatcher'


class LandingZoneState:
    def __init__(self, localInstallEnabled, landingZoneDescriptor=None, organizationDescriptor=None):
        self.localInstallEnabled = localInstallEnabled
        self.optLandingZoneDescriptor = landingZoneDescriptor
        self.optOrganizationDescriptor = organizationDescriptor

def landingZoneState(base :BaseState) -> LandingZoneState:
    landingZoneDiscovery = LandingZoneDiscovery(base.profile, requireRoleVerification=True)
    if base.args.forcelocal:
        print("Local installation has been specified")
        return LandingZoneState(True)
    landingZoneDescriptor = landingZoneDiscovery.getLandingZoneDescriptor()
    if landingZoneDescriptor.isStandalone:
        print("Landing zone is not configured. Will install locally.")
        return LandingZoneState(True)
    print('Detected {}'.format(landingZoneDescriptor.landingZoneType))
    organizationDescriptor = landingZoneDiscovery.getOrganizationDescriptor()
    print("Detected Organization ARN: {}".format(organizationDescriptor.arn))
    return LandingZoneState(False, landingZoneDescriptor, organizationDescriptor)

class EventBusState:
    def __init__(self, ruleArn):
        self.complianceChangeRuleArn = ruleArn

def eventBusState(clients :Clients, base :BaseState) -> EventBusState:
    eventBusArn = clients.eb.declareEventBusArn(base.eventBusName, base.tagsCore)
    print("EventBus ARN: {}".format(eventBusArn))
    ruleDesc= "Config Rule Compliance Change"
    eventPattern = {
        'source': ["aws.config"],
        'detail-type': ["Config Rules Compliance Change"]
    }
    ruleArn = clients.eb.declareEventBusRuleArn(
        base.eventBusName, base.complianceRuleName, ruleDesc, eventPattern, base.tagsCore
    )
    return EventBusState(ruleArn)

def eventBusRemove(clients : Clients, base: BaseState):
    clients.eb.removeEventBus(base.eventBusName)

class EventQueueState:
    def __init__(self, queueArn, cmkArn):
        self.queueArn = queueArn
        self.cmkArn = cmkArn

def eventQueueState(clients :Clients, base :BaseState, eventBus :EventBusState) -> EventQueueState:
    cfgPath = "cfg.core.coreQueueCfg"
    cfgMap = cfg.core.coreQueueCfg()
    eventBridge = policy.principalEventBridge()
    cmkStatements = [
        policy.allowCMKForServiceProducer(base.profile, policy.serviceNamespaceSQS(), eventBridge)
    ]
    cmkDesc = "Encryption for SQS queued events"
    cmkArn = clients.kms.declareCMKArn(cmkDesc, base.sqsCmkAlias, cmkStatements, base.tagsCore)
    print("Queue Encryption CMK ARN: {}".format(cmkArn))
    sqsStatements = [
         policy.allowSQSForServiceProducer(base.profile, base.queueName, eventBridge, eventBus.complianceChangeRuleArn)
    ]
    visibilityTimeoutSecs = getValue(cfgMap,cfgPath, 'SqsVisibilityTimeoutSecs')
    queueArn = clients.sqs.declareQueueArn(base.queueName, cmkArn, sqsStatements, visibilityTimeoutSecs, base.tagsCore)
    return EventQueueState(queueArn, cmkArn)

def eventQueueRemove(clients : Clients, base: BaseState):
    clients.sqs.removeQueue(base.queueName)
    if base.args.removecmks:
        clients.kms.removeCMK(base.sqsCmkAlias)

def eventQueueTarget(clients :Clients, base :BaseState, eventQueue :EventQueueState):
    cfgPath = "cfg.core.coreEventBusCfg"
    cfgMap = cfg.core.coreEventBusCfg()
    maxAgeSecs = getValue(cfgMap,cfgPath, 'RuleTargetMaxAgeSecs')
    clients.eb.declareEventBusTarget(
        base.eventBusName, base.complianceRuleName, base.queueName, eventQueue.queueArn, maxAgeSecs
    )

def eventBusPermission(clients :Clients, base :BaseState, landingZone :LandingZoneState):
    orgDesc :OrganizationDescriptor = landingZone.optOrganizationDescriptor
    if orgDesc:
        clients.eb.declareEventBusPublishPermissionForOrganization(base.eventBusName, orgDesc.id)
    else:
        clients.eb.declareEventBusPublishPermissionForAccount(base.eventBusName, base.profile.accountId)

class DispatchLambdaRoleState:
    def __init__(self, roleArn):
        self.roleArn = roleArn

def dispatchLambdaRoleState(clients :Clients, base :BaseState, queue :EventQueueState, landingZone :LandingZoneState) -> DispatchLambdaRoleState:
    lambdaPolicyArn = clients.iam.declareAwsPolicyArn(policy.awsLambdaBasicExecution())
    lambdaManagedPolicyArns = [lambdaPolicyArn]
    trustPolicy = policy.trustLambda()
    roleDesc = "Compliance Dispatcher Lambda Role"
    roleArn = clients.iam.declareRoleArn(base.dispatchLambdaRoleName, roleDesc, trustPolicy, base.tagsCore)
    clients.iam.declareManagedPoliciesForRole(base.dispatchLambdaRoleName, lambdaManagedPolicyArns)
    sqsPolicy = policy.permissions([policy.allowConsumeSQS(queue.queueArn), policy.allowDecryptCMK(queue.cmkArn)])
    ruleLambdaNamePattern = "function:{}".format(cfg.core.ruleFunctionName("*"))
    ruleLambdaArn = base.profile.getRegionAccountArn('lambda', ruleLambdaNamePattern)
    ruleInvokePolicy = policy.permissions([policy.allowInvokeLambda(ruleLambdaArn)])
    opsPolicy = policy.permissions([policy.allowPutCloudWatchMetricData()])
    inlinePolicyMap = {"ConsumeQueue": sqsPolicy, "InvokeRules": ruleInvokePolicy, "Operations": opsPolicy}
    orgDesc :OrganizationDescriptor = landingZone.optOrganizationDescriptor
    if orgDesc:
        lzStatements = [policy.allowDescribeIam("*"), policy.allowDescribeAccount(orgDesc.masterAccountId, orgDesc.id)]
        inlinePolicyMap['LandingZone'] = policy.permissions(lzStatements)
    clients.iam.declareInlinePoliciesForRole(base.dispatchLambdaRoleName, inlinePolicyMap)
    return DispatchLambdaRoleState(roleArn)

def dispatchLambdaRoleRemove(clients :Clients, base :BaseState):
    clients.iam.removeRole(base.dispatchLambdaRoleName)

def dispatchLambdaRoleVerify(clients :Clients, base :BaseState) -> DispatchLambdaRoleState:
    roleName = base.dispatchLambdaRoleName
    roleDesc :RoleDescriptor = clients.iam.getRoleDescriptor(roleName)
    if roleDesc: return DispatchLambdaRoleState(roleDesc.arn)
    msg = "Execution role `{}` for dispatch lambda has not yet been created via init command".format(roleName)
    raise ConfigError(msg)

class DispatchLambdaState:
    def __init__(self, lambdaArn):
        self.lambdaArn = lambdaArn

def dispatchLambdaState(clients: Clients, base: BaseState, role: DispatchLambdaRoleState) -> DispatchLambdaState:
    functionName = cfg.core.coreFunctionName(base.dispatchLambdaCodeName)
    functionDesc = 'Compliance Dispatcher Lambda'
    functionCfg = cfg.core.dispatchFunctionCfg()
    codeZip = codeLoader.getCoreCode(base.dispatchLambdaCodeName)
    lambdaArn = clients.lambdafun.declareFunctionArn(functionName, functionDesc, role.roleArn, functionCfg, codeZip, base.tagsCore)
    print("Core Dispatch Lambda ARN: {}".format(lambdaArn))
    return DispatchLambdaState(lambdaArn)

def dispatchLambdaRemove(clients: Clients, base: BaseState):
    functionName = cfg.core.coreFunctionName(base.dispatchLambdaCodeName)
    clients.lambdafun.removeFunction(functionName)

def init(args):
    profile = Profile()
    clients = Clients(args, profile)
    base = BaseState(args, profile)
    landingZone = landingZoneState(base)
    eventBus = eventBusState(clients, base)
    eventQueue = eventQueueState(clients, base, eventBus)
    eventQueueTarget(clients, base, eventQueue)
    eventBusPermission(clients, base, landingZone)
    dispatchLambdaRole = dispatchLambdaRoleState(clients, base, eventQueue, landingZone)
    dispatchLambda = dispatchLambdaState(clients, base, dispatchLambdaRole)

def code(args):
    profile = Profile()
    clients = Clients(args, profile)
    base = BaseState(args, profile)
    if args.core:
        dispatchLambdaRole = dispatchLambdaRoleVerify(clients, base)
        dispatchLambdaState(clients, base, dispatchLambdaRole)

def remove(args):
    profile = Profile()
    clients = Clients(args, profile)
    base = BaseState(args, profile)
    dispatchLambdaRemove(clients, base)
    dispatchLambdaRoleRemove(clients, base)
    eventQueueRemove(clients, base)
    eventBusRemove(clients, base)


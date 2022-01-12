from typing import List
from lib.base import Tags, ConfigError, DictBuild

from lib.rdq import Profile
from lib.rdq.svciam import IamClient, RoleDescriptor
from lib.rdq.svcorg import OrganizationClient, OrganizationDescriptor, OrganizationUnit, OrganizationUnitTree
from lib.rdq.svckms import KmsClient
from lib.rdq.svccfn import CfnClient
from lib.rdq.svceventbridge import EventBridgeClient
from lib.rdq.svcsqs import SqsClient
from lib.rdq.svclambda import LambdaClient

import lib.rdq.policy as policy

import lib.cfn as cfn
import lib.cfn.iam as iam
import lib.cfn.eventbridge as eb

import cfg.core
import cfg.roles
import cfg.org

from cmds.discovery import LandingZoneDiscovery, LandingZoneDescriptor
import cmds.codeLoader as codeLoader

def get_list(src: list, srcPath) -> list:
    if src is None: raise ConfigError("{} is undefined".format(srcPath))
    if len(src) == 0: raise ConfigError("{} is empty".format(srcPath))
    return src

def get_map(src: dict, srcPath) -> dict:
    if src is None: raise ConfigError("{} is undefined".format(srcPath))
    if len(src) == 0: raise ConfigError("{} is empty".format(srcPath))
    return src

def get_map_value(map, mapPath, key):
    value = get_map(map, mapPath).get(key, None)
    if value is None: raise ConfigError("{} in {} is undefined", key, mapPath)
    return value

def getCoreEventBusCfgValue(key): return get_map_value(cfg.core.coreEventBusCfg(), "cfg.core.coreEventBusCfg", key)
def getCoreQueueCfgValue(key): return get_map_value(cfg.core.coreQueueCfg(), "cfg.core.coreQueueCfg", key)
def getStandaloneRolesCfgValue(key): return get_map_value(cfg.roles.standaloneRoles(), "cfg.roles.standaloneRoles", key)


class Clients:
    def __init__(self, args, profile :Profile):
        self.iam = IamClient(profile)
        self.org = OrganizationClient(profile)
        self.kms = KmsClient(profile)
        self.cfn = CfnClient(profile)
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
        self.dispatchLambdaRoleName = cfg.core.coreResourceName('ComplianceDispatcherLambdaRole')
        self.dispatchLambdaCodeName = 'ComplianceDispatcher'
        self.dispatchFunctionName = cfg.core.coreFunctionName(self.dispatchLambdaCodeName)
        self.localAuditRoleName = getStandaloneRolesCfgValue('Audit')
        self.localRemediationRoleName = getStandaloneRolesCfgValue('Remediation')
        self.complianceForwarderStackName = cfg.core.coreResourceName('ComplianceChangeForwarder')
        self.complianceForwarderRoleName = cfg.core.coreResourceName('ComplianceChangeForwarderRole')
        self.complianceForwarderRuleName = cfg.core.coreResourceName('ComplianceChangeForwarderRule')

class LocalRoleState:
    def __init__(self, auditRoleArn, remediationRoleName):
        self.auditRoleArn = auditRoleArn
        self.remediationRoleName = remediationRoleName

def declareLocalAuditRoleArn(clients :Clients, base :BaseState):
    roleName = base.localAuditRoleName
    lambdaPolicyArn = clients.iam.declareAwsPolicyArn(policy.awsPolicyLambdaBasicExecution())
    trustPolicy = policy.trustLambda()
    roleDesc = "Local Audit Lambda Role"
    auditRoleArn = clients.iam.declareRoleArn(roleName, roleDesc, trustPolicy, base.tagsCore)
    clients.iam.declareManagedPoliciesForRole(roleName, [lambdaPolicyArn])
    remediationRoleArn = base.profile.getRoleArn(base.localRemediationRoleName)
    assumeRolePolicy = policy.permissions([policy.allowAssumeRole(remediationRoleArn)])
    inlinePolicyMap = {"AssumeRemediationRole": assumeRolePolicy}
    clients.iam.declareInlinePoliciesForRole(roleName, inlinePolicyMap)
    return auditRoleArn

def localRoleState(clients :Clients, base :BaseState) -> LocalRoleState:
    roleName = base.localRemediationRoleName
    adminPolicyArn = clients.iam.declareAwsPolicyArn(policy.awsPolicyAdministratorAccess())
    auditRoleArn = declareLocalAuditRoleArn(clients, base)
    trustPolicy = policy.trustRole(auditRoleArn)
    roleDesc = "Local Remediation Role"
    clients.iam.declareRoleArn(roleName, roleDesc, trustPolicy, base.tagsCore)
    clients.iam.declareManagedPoliciesForRole(roleName, [adminPolicyArn])
    return LocalRoleState(auditRoleArn, roleName)

def localRoleRemove(clients :Clients, base :BaseState):
    clients.iam.removeRole(base.localRemediationRoleName)
    clients.iam.removeRole(base.localAuditRoleName)

class OrganizationState:
    def __init__(self, organizationDescriptor: OrganizationDescriptor, ouList: List[OrganizationUnit], regionList):
        self.descriptor = organizationDescriptor
        self.ouList = ouList
        self.regionList = regionList

class LandingZoneState:
    def __init__(self, auditRoleArn, remediationRoleName, optOrganizationState: OrganizationState):
        self.auditRoleArn = auditRoleArn
        self.remediationRoleName = remediationRoleName
        self.optOrganizationState = optOrganizationState


def declareOrganizationState(base: BaseState, descriptor: OrganizationDescriptor, ouTree: OrganizationUnitTree) -> OrganizationState:
    orgId = descriptor.id
    cfgOUsInScope = get_list(cfg.org.organizationUnitsInScope(orgId), 'cfg.org.organizationUnitsInScope')
    cfgRegionsInScope = get_list(cfg.org.regionsInScope(orgId), 'cfg.org.regionsInScopeInScope')
    overOUsInScope = base.args.ous
    useCfg = overOUsInScope is None or len(overOUsInScope) == 0
    ouScopeList = []
    ousInScope = cfgOUsInScope if useCfg else overOUsInScope
    for oukey in ousInScope:
        ouMatch = ouTree.findOUById(oukey)
        if ouMatch:
            ouScopeList.append(ouMatch)
            continue
        ouMatch = ouTree.findOUByPath(oukey)
        if ouMatch:
            ouScopeList.append(ouMatch)
            continue
        ouMatchList = ouTree.matchOUByName(oukey)
        matchCount = len(ouMatchList)
        if matchCount == 1:
            ouScopeList.append(ouMatchList[0])
            continue
        if matchCount > 1:
            msg = "The OU name `{}` is used {} times in Organization {}; please specify the full OU path".format(oukey, matchCount, orgId)
        else:
            msg = "OU `{}` is not defined for Organization {}".format(oukey, orgId)
        raise ConfigError(msg)
    return OrganizationState(descriptor, ouScopeList, cfgRegionsInScope)


def landingZoneState(clients: Clients, base: BaseState) -> LandingZoneState:
    landingZoneDiscovery = LandingZoneDiscovery(base.profile)
    if base.args.forcelocal:
        print("Local installation has been specified")
        forceLocalRole = localRoleState(clients, base)
        return LandingZoneState(forceLocalRole.auditRoleArn, forceLocalRole.remediationRoleName, None)
    optLZDescriptor: LandingZoneDescriptor = landingZoneDiscovery.getLandingZoneDescriptor()
    if not optLZDescriptor:
        print("Landing zone is not configured. Will install locally.")
        requiredLocalRole = localRoleState(clients, base)
        return LandingZoneState(requiredLocalRole.auditRoleArn, requiredLocalRole.remediationRoleName, None)
    print('Detected {}'.format(optLZDescriptor.landingZoneType))
    organizationDescriptor = clients.org.getOrganizationDescriptor()
    print("Detected Organization ARN: {}".format(organizationDescriptor.arn))
    print("Enumerating OUs...")
    tracker = lambda depth, ouName: print(''.ljust(depth, '.')+ouName)
    ouTree = clients.org.getOrganizationUnitTree(tracker)
    print("...Done")
    print(ouTree.pretty())
    organizationState = declareOrganizationState(base, organizationDescriptor, ouTree)
    return LandingZoneState(optLZDescriptor.auditRoleArn, optLZDescriptor.remediationRoleName, organizationState)

class EventBusState:
    def __init__(self, eventBusArn, ruleArn):
        self.eventBusArn = eventBusArn
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
    return EventBusState(eventBusArn, ruleArn)

def eventBusRemove(clients : Clients, base: BaseState):
    eventBusName = base.eventBusName
    clients.eb.removeEventBus(eventBusName)
    print("Removed {}".format(eventBusName))

class EventQueueState:
    def __init__(self, queueArn, cmkArn):
        self.queueArn = queueArn
        self.cmkArn = cmkArn

def eventQueueState(clients :Clients, base :BaseState, eventBus :EventBusState) -> EventQueueState:
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
    visibilityTimeoutSecs = getCoreQueueCfgValue('SqsVisibilityTimeoutSecs')
    queueArn = clients.sqs.declareQueueArn(base.queueName, cmkArn, sqsStatements, visibilityTimeoutSecs, base.tagsCore)
    print("Queue ARN: {}".format(queueArn))
    return EventQueueState(queueArn, cmkArn)

def eventQueueRemove(clients : Clients, base: BaseState):
    queueName = base.queueName
    clients.sqs.removeQueue(queueName)
    print("Removed {}".format(queueName))
    if base.args.removecmks:
        alias = base.sqsCmkAlias
        clients.kms.removeCMK(alias)
        print("Scheduled removal of {}".format(alias))

def eventQueueTarget(clients :Clients, base :BaseState, eventQueue :EventQueueState):
    maxAgeSecs = getCoreEventBusCfgValue('RuleTargetMaxAgeSecs')
    clients.eb.declareEventBusTarget(
        base.eventBusName, base.complianceRuleName, base.queueName, eventQueue.queueArn, maxAgeSecs
    )

def eventBusPermission(clients :Clients, base :BaseState, landingZone :LandingZoneState):
    organizationState = landingZone.optOrganizationState
    if organizationState:
        organizationId = organizationState.descriptor.id
        clients.eb.declareEventBusPublishPermissionForOrganization(base.eventBusName, organizationId)
    else:
        clients.eb.declareEventBusPublishPermissionForAccount(base.eventBusName, base.profile.accountId)

class DispatchLambdaRoleState:
    def __init__(self, roleArn):
        self.roleArn = roleArn

def dispatchLambdaRoleState(clients :Clients, base :BaseState, queue :EventQueueState, landingZone :LandingZoneState) -> DispatchLambdaRoleState:
    lambdaPolicyArn = clients.iam.declareAwsPolicyArn(policy.awsPolicyLambdaBasicExecution())
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
    clients.iam.declareInlinePoliciesForRole(base.dispatchLambdaRoleName, inlinePolicyMap)
    return DispatchLambdaRoleState(roleArn)

def dispatchLambdaRoleRemove(clients :Clients, base :BaseState):
    roleName = base.dispatchLambdaRoleName
    clients.iam.removeRole(roleName)
    print("Removed {}".format(roleName))

def dispatchLambdaRoleVerify(clients :Clients, base :BaseState) -> DispatchLambdaRoleState:
    roleName = base.dispatchLambdaRoleName
    roleDesc :RoleDescriptor = clients.iam.getRoleDescriptor(roleName)
    if roleDesc: return DispatchLambdaRoleState(roleDesc.arn)
    msg = "Execution role `{}` for dispatch lambda has not yet been created via init command".format(roleName)
    raise ConfigError(msg)

class DispatchLambdaState:
    def __init__(self, lambdaArn):
        self.lambdaArn = lambdaArn

def dispatchLambdaState(clients: Clients, base: BaseState, role: DispatchLambdaRoleState, landingZone :LandingZoneState) -> DispatchLambdaState:
    functionName = base.dispatchFunctionName
    functionDesc = 'Compliance Dispatcher Lambda'
    functionCfgBuild = DictBuild(cfg.core.dispatchFunctionCfg())
    envKey = "Environment.Variables.{}".format(cfg.core.environmentVariableNameRemediationRole())
    functionCfgBuild.extend(envKey, landingZone.remediationRoleName)
    functionCfg = functionCfgBuild.toDict()
    codeZip = codeLoader.getCoreCode(base.dispatchLambdaCodeName)
    lambdaArn = clients.lambdafun.declareFunctionArn(functionName, functionDesc, role.roleArn, functionCfg, codeZip, base.tagsCore)
    print("Core Dispatch Lambda ARN: {}".format(lambdaArn))
    return DispatchLambdaState(lambdaArn)

def dispatchLambdaRemove(clients: Clients, base: BaseState):
    functionName = base.dispatchFunctionName
    clients.lambdafun.removeFunction(functionName)
    print("Removed {}".format(functionName))

def dispatchLambdaQueueConsumerState(clients: Clients, base: BaseState, dispatchLambda: DispatchLambdaState, eventQueue: EventQueueState):
    sqsPollCfg = getCoreQueueCfgValue('SqsPollCfg')
    uuid = clients.lambdafun.declareEventSourceMappingUUID(base.dispatchFunctionName, eventQueue.queueArn, sqsPollCfg)
    print("Queue {} is mapped as event source for {} (UUID {})".format(eventQueue.queueArn, dispatchLambda.lambdaArn, uuid))

def dispatchLambdaQueueConsumerRemove(clients: Clients, base: BaseState):
    clients.lambdafun.removeEventSourceMappingsForFunction(base.dispatchFunctionName)

def ruleLambdaState(clients: Clients, base: BaseState, landingZone :LandingZoneState):
    roleArn = landingZone.auditRoleArn
    ruleFolders = codeLoader.getAvailableRules()
    for ruleFolder in ruleFolders:
        codeZip = codeLoader.getRuleCode(ruleFolder)
        functionName = cfg.core.ruleFunctionName(ruleFolder)
        functionDesc = '{} Auto Remediation Lambda'.format(ruleFolder)
        functionCfg = cfg.core.ruleFunctionCfg(ruleFolder)
        lambdaArn = clients.lambdafun.declareFunctionArn(functionName, functionDesc, roleArn, functionCfg, codeZip, base.tagsCore)
        print("Rule Lambda ARN: {}".format(lambdaArn))

def ruleLambdaRemove(clients: Clients, base: BaseState):
    ruleFolders = codeLoader.getAvailableRules()
    for ruleFolder in ruleFolders:
        functionName = cfg.core.ruleFunctionName(ruleFolder)
        clients.lambdafun.removeFunction(functionName)
        print("Removed {}".format(functionName))


def complianceForwarderState(clients: Clients, base: BaseState, eventBus :EventBusState, landingZone :LandingZoneState):
    roleName = base.complianceForwarderRoleName
    roleDesc = "Allow config rule compliance chance events to be forwarded to central event bus"
    templateDesc = "Compliance Change Event Forwarder"
    arnTargetEventBus = eventBus.eventBusArn
    ruleName = base.complianceForwarderRuleName
    resourceMap = {}
    allowEventBusPutEvent = iam.Allow([eb.iamPutEvents], [arnTargetEventBus])
    policyDocument = iam.PolicyDocument([allowEventBusPutEvent])
    inlinePolicy = iam.InlinePolicy("CentralBusForwarderPolicy", policyDocument)
    trustPolicy = iam.TrustPolicy(eb.iamPrincipal)
    _rRole = 'rRole'
    _rEventRule = 'rEventRule'
    resourceMap[_rRole] = iam.IAM_Role(roleName, roleDesc, trustPolicy, None, [inlinePolicy])
    ruleTarget = eb.Target('CentralBus', arnTargetEventBus, cfn.Arn(_rRole))
    eventPattern = eb.EventPattern_ConfigComplianceChange()
    resourceMap[_rEventRule] = eb.rRule('default', ruleName, eventPattern, [ruleTarget])
    templateMap = cfn.Template(templateDesc, resourceMap)
    stackName = base.complianceForwarderStackName
    optOrganizationState = landingZone.optOrganizationState
    if optOrganizationState:
        ouList = optOrganizationState.ouList
        regionList = optOrganizationState.regionList
        operationRef = clients.cfn.declareStackSet(stackName, templateMap, templateDesc, base.tagsCore, ouList, regionList)
        print("Compliance Forwarder Stack Set Id: {} (Operation: {})".format(operationRef.stackSetId, operationRef.operationId))
    else:
        stackId = clients.cfn.declareStack(stackName, templateMap, base.tagsCore)
        print("Stack Id: {}".format(stackId))

def complianceForwarderRemove(clients: Clients, base: BaseState):
    stackName = base.complianceForwarderStackName
    print("Removing {}...".format(stackName))
    clients.cfn.removeStack(stackName)
    clients.cfn.removeStackSet(stackName)
    print("Removed {}".format(stackName))

def init(args):
    profile = Profile()
    clients = Clients(args, profile)
    base = BaseState(args, profile)
    landingZone = landingZoneState(clients, base)
    eventBus = eventBusState(clients, base)
    eventQueue = eventQueueState(clients, base, eventBus)
    eventQueueTarget(clients, base, eventQueue)
    eventBusPermission(clients, base, landingZone)
    dispatchLambdaRole = dispatchLambdaRoleState(clients, base, eventQueue, landingZone)
    dispatchLambda = dispatchLambdaState(clients, base, dispatchLambdaRole, landingZone)
    dispatchLambdaQueueConsumerState(clients, base, dispatchLambda, eventQueue)
    ruleLambdaState(clients, base, landingZone)
    complianceForwarderState(clients, base, eventBus, landingZone)

def codeCore(clients, base):
    dispatchLambdaRole = dispatchLambdaRoleVerify(clients, base)
    dispatchLambdaState(clients, base, dispatchLambdaRole)

def code(args):
    profile = Profile()
    clients = Clients(args, profile)
    base = BaseState(args, profile)
    if args.core:
        codeCore(clients, base)

def remove(args):
    profile = Profile()
    clients = Clients(args, profile)
    base = BaseState(args, profile)
    complianceForwarderRemove(clients, base)
    ruleLambdaRemove(clients, base)
    dispatchLambdaQueueConsumerRemove(clients, base)
    dispatchLambdaRemove(clients, base)
    dispatchLambdaRoleRemove(clients, base)
    eventQueueRemove(clients, base)
    eventBusRemove(clients, base)
    localRoleRemove(clients, base)


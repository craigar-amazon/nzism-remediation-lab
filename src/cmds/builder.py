from typing import List
from lib.base import Tags, ConfigError, DictBuild

from lib.rdq import Profile
from lib.rdq.svciam import IamClient, RoleDescriptor
from lib.rdq.svcorg import OrganizationClient, OrganizationDescriptor, OrganizationUnit
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

def get_list_len(src: list, srcPath) -> list:
    if src is None: raise ConfigError("{} is undefined".format(srcPath))
    return len(src)

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

def get_lambda_concurrency():
    return {'ReservedConcurrentExecutions': 1}

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
        lzSearchPathLen = get_list_len(cfg.roles.landingZoneSearch(), "cfg.roles.landingZoneSearch")
        self.isLocal = args.forcelocal or (lzSearchPathLen == 0)

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
    if base.isLocal:
        clients.iam.removeRole(base.localRemediationRoleName)
        clients.iam.removeRole(base.localAuditRoleName)

class OrganizationState:
    def __init__(self, organizationDescriptor: OrganizationDescriptor, ouList: List[OrganizationUnit], regionList):
        self.descriptor = organizationDescriptor
        self.ouList = ouList
        self.regionList = regionList

def organizationState(clients: Clients, base: BaseState) -> OrganizationState:
    if base.isLocal: return None
    descriptor = clients.org.getOrganizationDescriptor()
    print("Detected Organization ARN: {}".format(descriptor.arn))
    print("Enumerating OUs...")
    tracker = lambda depth, ouName: print(''.ljust(depth, '.')+ouName)
    ouTree = clients.org.getOrganizationUnitTree(tracker)
    print("...Done")
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
            ouScopeList.append(ouMatch.id)
            continue
        ouMatch = ouTree.findOUByPath(oukey)
        if ouMatch:
            ouScopeList.append(ouMatch.id)
            continue
        ouMatchList = ouTree.matchOUByName(oukey)
        matchCount = len(ouMatchList)
        if matchCount == 1:
            ouScopeList.append(ouMatchList[0].id)
            continue
        if matchCount > 1:
            msg = "The OU name `{}` is used {} times in Organization {}; please specify the full OU path".format(oukey, matchCount, orgId)
        else:
            msg = "OU `{}` is not defined for Organization {}".format(oukey, orgId)
        raise ConfigError(msg)
    print(ouTree.pretty(highlightIds=ouScopeList, caption="<<--Compliance Forwarding"))
    return OrganizationState(descriptor, ouScopeList, cfgRegionsInScope)

class LandingZoneState:
    def __init__(self, auditRoleArn, remediationRoleName):
        self.auditRoleArn = auditRoleArn
        self.remediationRoleName = remediationRoleName

def landingZoneState(clients: Clients, base: BaseState) -> LandingZoneState:
    if base.isLocal:
        print("Local installation has been specified")
        localRole = localRoleState(clients, base)
        return LandingZoneState(localRole.auditRoleArn, localRole.remediationRoleName)
    landingZoneDiscovery = LandingZoneDiscovery(base.profile)
    lzDescriptor: LandingZoneDescriptor = landingZoneDiscovery.getLandingZoneDescriptor()
    print('Detected {}'.format(lzDescriptor.landingZoneType))
    return LandingZoneState(lzDescriptor.auditRoleArn, lzDescriptor.remediationRoleName)


class EventBusState:
    def __init__(self, eventBusArn, ruleArn):
        self.eventBusArn = eventBusArn
        self.complianceChangeRuleArn = ruleArn

def eventBusState(clients :Clients, base :BaseState) -> EventBusState:
    busName = base.eventBusName
    ruleName = base.complianceRuleName
    eventBusArn = clients.eb.declareEventBusArn(base.eventBusName, base.tagsCore)
    print("EventBus ARN: {}".format(eventBusArn))
    ruleDesc= "Config Rule Compliance Change"
    eventPattern = {
        'source': ["aws.config"],
        'detail-type': ["Config Rules Compliance Change"]
    }
    ruleArn = clients.eb.declareEventBusRuleArn(busName, ruleName, ruleDesc, eventPattern, base.tagsCore)
    return EventBusState(eventBusArn, ruleArn)

def eventBusRemove(clients : Clients, base: BaseState):
    busName = base.eventBusName
    clients.eb.removeEventBus(busName)
    print("Removed {}".format(busName))

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
    busName = base.eventBusName
    ruleName = base.complianceRuleName
    queueName = base.queueName
    maxAgeSecs = getCoreEventBusCfgValue('RuleTargetMaxAgeSecs')
    clients.eb.declareEventBusTarget(busName, ruleName, queueName, eventQueue.queueArn, maxAgeSecs)

def eventBusPermission(clients :Clients, base :BaseState, optOrganization :OrganizationState):
    if optOrganization:
        organizationId = optOrganization.descriptor.id
        clients.eb.declareEventBusPublishPermissionForOrganization(base.eventBusName, organizationId)
    else:
        clients.eb.declareEventBusPublishPermissionForAccount(base.eventBusName, base.profile.accountId)

class DispatchLambdaRoleState:
    def __init__(self, roleArn):
        self.roleArn = roleArn

def dispatchLambdaRoleState(clients :Clients, base :BaseState, queue :EventQueueState, optOrganization :OrganizationState) -> DispatchLambdaRoleState:
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
    opsActions = [policy.allowPutCloudWatchMetricData()]
    if optOrganization:
        orgDesc = optOrganization.descriptor
        opsActions.append(policy.allowDescribeAccount(orgDesc.masterAccountId, orgDesc.id))
    opsPolicy = policy.permissions(opsActions)
    inlinePolicyMap = {"ConsumeQueue": sqsPolicy, "InvokeRules": ruleInvokePolicy, "Operations": opsPolicy}
    clients.iam.declareInlinePoliciesForRole(base.dispatchLambdaRoleName, inlinePolicyMap)
    print("Core Dispatch Lambda Role ARN: {}".format(roleArn))
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
    roleArn = role.roleArn
    functionDesc = 'Compliance Dispatcher Lambda'
    functionCfgBuild = DictBuild(cfg.core.dispatchFunctionCfg())
    envKey = "Environment.Variables.{}".format(cfg.core.environmentVariableNameRemediationRole())
    functionCfgBuild.extend(envKey, landingZone.remediationRoleName)
    functionCfg = functionCfgBuild.toDict()
    concurrency = get_lambda_concurrency()
    codeZip = codeLoader.getCoreCode(base.dispatchLambdaCodeName)
    lambdaArn = clients.lambdafun.declareFunctionArn(functionName, functionDesc, roleArn, functionCfg, concurrency, codeZip, base.tagsCore)
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
    tags = base.tagsCore
    roleArn = landingZone.auditRoleArn
    concurrency = get_lambda_concurrency()
    ruleFolders = codeLoader.getAvailableRules()
    for ruleFolder in ruleFolders:
        codeZip = codeLoader.getRuleCode(ruleFolder)
        functionName = cfg.core.ruleFunctionName(ruleFolder)
        functionDesc = '{} Auto Remediation Lambda'.format(ruleFolder)
        functionCfg = cfg.core.ruleFunctionCfg(ruleFolder)
        lambdaArn = clients.lambdafun.declareFunctionArn(functionName, functionDesc, roleArn, functionCfg, concurrency, codeZip, tags)
        print("Rule Lambda ARN: {}".format(lambdaArn))

def ruleLambdaRemove(clients: Clients, base: BaseState):
    ruleFolders = codeLoader.getAvailableRules()
    for ruleFolder in ruleFolders:
        functionName = cfg.core.ruleFunctionName(ruleFolder)
        clients.lambdafun.removeFunction(functionName)
        print("Removed {}".format(functionName))


def complianceForwarderState(clients: Clients, base: BaseState, eventBus :EventBusState, optOrganization :OrganizationState):
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
    if optOrganization:
        ouList = optOrganization.ouList
        regionList = optOrganization.regionList
        operationRef = clients.cfn.declareStackSet(stackName, templateMap, templateDesc, base.tagsCore, ouList, regionList)
        opInfo = "Operation: {}".format(operationRef.operationId) if operationRef.operationId else "No stack operations required"
        print("Compliance Forwarder Stack Set Id: {} | {}".format(operationRef.stackSetId, opInfo))
    else:
        stackId = clients.cfn.declareStack(stackName, templateMap, base.tagsCore)
        print("Stack Id: {}".format(stackId))

def complianceForwarderRemove(clients: Clients, base: BaseState):
    stackName = base.complianceForwarderStackName
    print("Removing {}...".format(stackName))
    if base.isLocal:
        clients.cfn.removeStack(stackName)
    else:
        clients.cfn.removeStackSet(stackName)
    print("Removed {}".format(stackName))

def complianceForwarderView(clients: Clients, base: BaseState):
    stackName = base.complianceForwarderStackName
    if base.isLocal:
        ss = clients.cfn.getStack(stackName)
        status = ss.status if ss.status else '-'
        if ss.statusReason:
            status = status + " (" + ss.statusReason + ")"
        print("Local Compliance Forwarder | Status: {}".format(status))
    else:
        siList = clients.cfn.listStackInstances(stackName)
        print("Compliance Forwarders:")
        for si in siList:
            accountDesc = clients.org.getAccountDescriptor(si.account)
            if accountDesc:
                accountInfo = "{} - {} {} ({})".format(accountDesc.accountName, si.account, accountDesc.status, si.ouId)
            else:
                accountInfo = "{} ({})".format(si.account, si.ouId)
            status = si.status if si.status else '-'
            if si.statusReason:
                status = status + " (" + si.statusReason + ")"
            stackStatus = si.stackInstanceStatus if si.stackInstanceStatus else '-'
            print("> {} {} | Status: {} | Stack: {}".format(accountInfo, si.region, status, stackStatus))


def init(args):
    profile = Profile()
    clients = Clients(args, profile)
    base = BaseState(args, profile)
    landingZone = landingZoneState(clients, base)
    optOrganization = organizationState(clients, base)
    eventBus = eventBusState(clients, base)
    eventQueue = eventQueueState(clients, base, eventBus)
    eventQueueTarget(clients, base, eventQueue)
    eventBusPermission(clients, base, optOrganization)
    dispatchLambdaRole = dispatchLambdaRoleState(clients, base, eventQueue, optOrganization)
    dispatchLambda = dispatchLambdaState(clients, base, dispatchLambdaRole, landingZone)
    dispatchLambdaQueueConsumerState(clients, base, dispatchLambda, eventQueue)
    ruleLambdaState(clients, base, landingZone)
    complianceForwarderState(clients, base, eventBus, optOrganization)

def code(args):
    profile = Profile()
    clients = Clients(args, profile)
    base = BaseState(args, profile)
    landingZone = landingZoneState(clients, base)
    if args.core:
        dispatchLambdaRole = dispatchLambdaRoleVerify(clients, base)
        dispatchLambdaState(clients, base, dispatchLambdaRole, landingZone)
    if args.rules:
        ruleLambdaState(clients, base, landingZone)

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

def view(args):
    profile = Profile()
    clients = Clients(args, profile)
    base = BaseState(args, profile)
    if args.forwarders:
        complianceForwarderView(clients, base)

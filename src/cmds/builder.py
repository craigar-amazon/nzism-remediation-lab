from lib.base import Tags, ConfigError

from lib.rdq import Profile
from lib.rdq.svcorg import OrganizationClient, OrganizationDescriptor
from lib.rdq.svckms import KmsClient
from lib.rdq.svceventbridge import EventBridgeClient
from lib.rdq.svcsqs import SqsClient

import lib.rdq.policy as policy


from lib.lambdas.discovery import LandingZoneDiscovery

import cfg.core
import cmds.codeLoader

def getValue(map, mapPath, key):
    if map is None: raise ConfigError("{} is undefined".format(mapPath))
    if len(map) == 0: raise ConfigError("{} is empty".format(mapPath))
    value = map.get(key, None)
    if value is None: raise ConfigError("{} in {} is undefined", key, mapPath)
    return value

class Clients:
    def __init__(self, args, profile :Profile):
        self.kms = KmsClient(profile)
        self.eventbridge = EventBridgeClient(profile)
        self.sqs = SqsClient(profile)

class BaseState:
    def __init__(self, args, profile :Profile):
        self.args = args
        self.profile = profile
        self.tagsCore = Tags(cfg.core.coreResourceTags(), context="cfg.core.coreResourceTags")
        self.eventBusName = cfg.core.coreResourceName('AutoRemediationEventBus')
        self.complianceRuleName = cfg.core.coreResourceName('ComplianceChangeRule')
        self.sqsCmkAlias = cfg.core.coreQueueCMKAlias()
        self.queueName = cfg.core.coreResourceName('ComplianceChangeQueue')

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
    eventBusArn = clients.eventbridge.declareEventBusArn(base.eventBusName, base.tagsCore)
    print("EventBus ARN: {}".format(eventBusArn))
    ruleDesc= "Config Rule Compliance Change"
    eventPattern = {
        'source': ["aws.config"],
        'detail-type': ["Config Rules Compliance Change"]
    }
    ruleArn = clients.eventbridge.declareEventBusRuleArn(
        base.eventBusName, base.complianceRuleName, ruleDesc, eventPattern, base.tagsCore
    )
    return EventBusState(ruleArn)

def eventBusRemove(clients : Clients, base: BaseState):
    clients.eventbridge.removeEventBus(base.eventBusName)

class EventQueueState:
    def __init__(self, queueArn):
        self.queueArn = queueArn

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
    return EventQueueState(queueArn)

def eventQueueRemove(clients : Clients, base: BaseState):
    if base.args.removecmks:
        clients.kms.removeCMK(base.sqsCmkAlias)

def eventQueueTarget(clients :Clients, base :BaseState, eventQueue :EventQueueState):
    cfgPath = "cfg.core.coreEventBusCfg"
    cfgMap = cfg.core.coreEventBusCfg()
    maxAgeSecs = getValue(cfgMap,cfgPath, 'RuleTargetMaxAgeSecs')
    clients.eventbridge.declareEventBusTarget(
        base.eventBusName, base.complianceRuleName, base.queueName, eventQueue.queueArn, maxAgeSecs
    )

def eventBusPermission(clients :Clients, base :BaseState, landingZone :LandingZoneState):
    if landingZone.localInstallEnabled:
        clients.eventbridge.declareEventBusPublishPermissionForAccount(base.eventBusName, base.profile.accountId)
    else:
        orgDesc :OrganizationDescriptor = landingZone.optOrganizationDescriptor
        clients.eventbridge.declareEventBusPublishPermissionForOrganization(base.eventBusName, orgDesc.id)

def install(args):
    profile = Profile()
    clients = Clients(args, profile)
    base = BaseState(args, profile)
    landingZone = landingZoneState(base)
    eventBus = eventBusState(clients, base)
    eventQueue = eventQueueState(clients, base, eventBus)
    eventQueueTarget(clients, base, eventQueue)
    eventBusPermission(clients, base, landingZone)


def remove(args):
    profile = Profile()
    clients = Clients(args, profile)
    base = BaseState(args, profile)
    eventBusRemove(clients, base)
    eventQueueRemove(clients, base)


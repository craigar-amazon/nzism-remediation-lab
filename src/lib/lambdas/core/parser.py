import logging
import json
from typing import List

from lib.base import RK
import cfg.core as cfgCore
import cfg.rules as cfgRules

from lib.rdq import Profile
from lib.rdq.svcorg import OrganizationClient, AccountDescriptor
from lib.base.request import DispatchEvent, DispatchEventTarget
import lib.lambdas.core.ruleselector as ruleselector
import lib.lambdas.core.filter as filter

class TargetDescriptor:
    def __init__(self, props):
        self._props = props
    
    @property
    def accountName(self): return self._props.get('AccountName')

    @property
    def accountEmail(self): return self._props.get('AccountEmail')

    @property
    def roleName(self): return self._props.get('RoleName')

    @property
    def isActive(self): return self._props.get('StatusActive')

    def toDict(self): return self._props
        

class RuleInvocation:
    def __init__(self, functionName :str, event :DispatchEvent, attempt=1):
        self._functionName = functionName
        self._event = event
        self._attempt = attempt

    @property
    def functionName(self) -> str: return self._functionName

    @property
    def attempt(self) -> int: return self._attempt

    @property
    def event(self) -> DispatchEvent: return self._event

    def newInvocation(self):
        return RuleInvocation(self._functionName, self._event, self._attempt + 1)

    def toDict(self):
        d = dict()
        d['functionName'] = self._functionName
        d['attempt'] = self._attempt
        d['event'] = self._event.toDict()
        return d

    def __str__(self):
        return json.dumps(self.toDict())

class Parser:
    def __init__(self, profile:Profile, remediationRoleName: str, isStandaloneMode: bool):
        self._profile = profile
        self._orgclient = OrganizationClient(profile)
        self._remediationRoleName = remediationRoleName
        self._isStandaloneMode = isStandaloneMode
        self._accountDescriptorMap = {}

    def get_target(self, accountId) -> TargetDescriptor:
        isExternalAccount = self._profile.accountId != accountId
        if self._isStandaloneMode and isExternalAccount:
            report = {RK.Synopsis: "SkippingAccount", 'AccountId': accountId, RK.Cause: 'External accounts are ignored in standalone mode'}
            logging.info(report)
            return None
        
        if self._isStandaloneMode:
            propsLocal = {
                'RoleName': self._remediationRoleName,
                'AccountName': 'local',
                'AccountEmail': 'local@local',
                'StatusActive': True
            }
            return TargetDescriptor(propsLocal)

        exTargetDesc = self._accountDescriptorMap.get(accountId)
        if exTargetDesc: return exTargetDesc

        accountDesc: AccountDescriptor = self._orgclient.getAccountDescriptor(accountId)
        props = {
            'RoleName': self._remediationRoleName,
            'AccountName': accountDesc.accountName,
            'AccountEmail': accountDesc.accountEmail,
            'StatusActive': accountDesc.isActive
        }
        newTargetDesc = TargetDescriptor(props)
        self._accountDescriptorMap[accountId] = newTargetDesc
        return newTargetDesc

    def get_preview(self, configRuleName, action, accountName):
        preview = cfgRules.isPreview(configRuleName, action, accountName)
        if not (preview is None): return preview
        return True

    def get_deployment_method(self, configRuleName, action, accountName):
        dm = cfgRules.deploymentMethod(configRuleName, action, accountName)
        if not (dm is None): return dm
        return {}

    def get_stack_name_pattern(self, configRuleName, action, accountName):
        pattern = cfgRules.stackNamePattern(configRuleName, action, accountName)
        if not (pattern is None): return pattern
        conformancePackName = cfgRules.conformancePackName()
        pattern = conformancePackName + "-AutoDeploy-{}"
        return pattern

    def get_manual_tag_name(self, configRuleName, action, accountName):
        tagName = cfgRules.manualTagName(configRuleName, action, accountName)
        if not (tagName is None): return tagName
        tagName = "DoNotAutoRemediate"
        report = {
            RK.Synopsis: "PartialConfig",
            'Rule': configRuleName,
            RK.Cause: "No manual remediation tag defined by rule",
            RK.Mitigation: "Will use {}".format(tagName)
        }
        logging.warning(report)
        return tagName

    def get_auto_resource_tags(self, configRuleName, action, accountName):
        tags = cfgRules.autoResourceTags(configRuleName, action, accountName)
        if not (tags is None): return tags
        tags = {'AutoDeployed': 'True'}
        report = {
            RK.Synopsis: "PartialConfig",
            'Rule': configRuleName,
            RK.Cause: "No tags defined for auto-deployed resources by rule",
            RK.Mitigation: "Will use tags {}".format(tags)
        }
        logging.warning(report)
        return tags


    def create_invoke(self, dispatch):
        action = dispatch['action']
        targetAccountId = dispatch['awsAccountId']
        resourceId = dispatch['resourceId']
        optTargetDescriptor = self.get_target(targetAccountId)
        if not optTargetDescriptor: return None
        if not optTargetDescriptor.isActive:
            report = {RK.Synopsis: "AccountNotActive", 'Dispatch': dispatch, 'Target': optTargetDescriptor.toDict()}
            logging.info(report)
            return None
        targetAccountName = optTargetDescriptor.accountName
        configRuleName = dispatch['configRuleNameBase']
        ruleCodeFolder = ruleselector.getRuleCodeFolder(configRuleName, action, targetAccountName)
        if not ruleCodeFolder:
            report = {RK.Synopsis: "NoRuleImplementation", 'Dispatch': dispatch, 'Target': optTargetDescriptor.toDict()}
            logging.info(report)
            return None
        if not ruleselector.isActionEnabled(action, configRuleName, targetAccountName):
            report = {RK.Synopsis: "ActionDisabled", 'Dispatch': dispatch, 'Target': optTargetDescriptor.toDict()}
            logging.info(report)
            return None
        functionName = cfgCore.ruleFunctionName(ruleCodeFolder)
        acceptResource = filter.acceptResourceId(configRuleName, action, targetAccountName, resourceId)
        if not acceptResource:
            report = {RK.Synopsis: "ResourceExempt", 'Dispatch': dispatch, 'Target': optTargetDescriptor.toDict()}
            logging.info(report)
            return None

        det = {}
        det['awsAccountId'] = targetAccountId
        det['awsAccountName'] = targetAccountName
        det['awsAccountEmail'] = optTargetDescriptor.accountEmail
        det['awsRegion'] = dispatch['awsRegion']
        det['roleName'] = optTargetDescriptor.roleName
        det['resourceType'] = dispatch['resourceType']
        det['resourceId'] = resourceId
        target = DispatchEventTarget(det)
        de = {}
        de['configRuleName'] = configRuleName
        de['action'] = action
        de['conformancePackName'] = cfgRules.conformancePackName()
        de['preview'] = self.get_preview(configRuleName, action, targetAccountName)
        de['deploymentMethod'] = self.get_deployment_method(configRuleName, action, targetAccountName)
        de['manualTagName'] = self.get_manual_tag_name(configRuleName, action, targetAccountName)
        de['autoResourceTags'] = self.get_auto_resource_tags(configRuleName, action, targetAccountName)
        de['stackNamePattern'] = self.get_stack_name_pattern(configRuleName, action, targetAccountName)
        event = DispatchEvent(de, target)
        return {'functionName': functionName, 'event': event}

    def createInvokeList(self, dispatchList) -> List[RuleInvocation]:
        invokeList = []
        for dispatch in dispatchList:
            optInvoke = self.create_invoke(dispatch)
            if not optInvoke: continue
            invoke = RuleInvocation(optInvoke['functionName'], optInvoke['event'])
            invokeList.append(invoke)
        return invokeList

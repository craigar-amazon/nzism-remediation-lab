import logging
import json
from typing import List

import cfg.core as cfgCore
import cfg.rules as cfgrules

from lib.rdq import Profile
from lib.base import ConfigError
from lib.base.request import DispatchEvent, DispatchEventTarget
from lib.lambdas.discovery import LandingZoneDiscovery
import lib.lambdas.core.filter as filter

keywordLocalAccount = 'LOCAL'

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
    def __init__(self, profile :Profile):
        self._profile = profile
        self._discover = LandingZoneDiscovery(profile)

    def get_account_desc(self, optLandingZone, accountId):
        if not optLandingZone:
            return {
                'Name': keywordLocalAccount,
                'Email': keywordLocalAccount
            }
        targetDesc = self._discover.getAccountDescriptor(accountId)
        if not targetDesc.isActive:
            logging.info("Skipping account %s with status %s", accountId, targetDesc.status)
            return None
        return {
            'Name': targetDesc.accountName,
            'Email': targetDesc.accountEmail
        }

    def get_target_role(self, optLandingZone, accountId):
        targetRole = None
        if optLandingZone:
            targetRole = optLandingZone['RemediationRoleName']
        else:
            if self._profile.accountId == accountId:
                targetRole = keywordLocalAccount
        if not targetRole:
            erm = "Cannot remediate account {} without a remediation role".format(accountId)
            logging.error(erm)
            raise ConfigError(erm)
        return targetRole

    def get_preview(self, configRuleName, action, accountName):
        preview = cfgrules.isPreview(configRuleName, action, accountName)
        if not (preview is None): return preview
        return True

    def get_deployment_method(self, configRuleName, action, accountName):
        dm = cfgrules.deploymentMethod(configRuleName, action, accountName)
        if not (dm is None): return dm
        return {}

    def get_stack_name_pattern(self, configRuleName, action, accountName):
        pattern = cfgrules.stackNamePattern(configRuleName, action, accountName)
        if not (pattern is None): return pattern
        conformancePackName = cfgrules.conformancePackName()
        pattern = conformancePackName + "-AutoDeploy-{}"
        return pattern

    def get_manual_tag_name(self, configRuleName, action, accountName):
        tagName = cfgrules.manualRemediationTagName(configRuleName, action, accountName)
        if not (tagName is None): return tagName
        tagName = "DoNotAutoRemediate"
        logging.warning("No manual remediation tag defined for rule %s; will use %s", configRuleName, tagName)
        return tagName

    def get_auto_resource_tags(self, configRuleName, action, accountName):
        tags = cfgrules.autoResourceTags(configRuleName, action, accountName)
        if not (tags is None): return tags
        tags = {'AutoDeployed': 'True'}
        logging.warning("No tags defined for auto-deployed resources by rule %s; will use %s", configRuleName, tags)
        return tags


    def create_invoke(self, optLandingZone, dispatch):
        action = dispatch['action']
        targetAccountId = dispatch['awsAccountId']
        resourceId = dispatch['resourceId']
        optTargetDesc = self.get_account_desc(optLandingZone, targetAccountId)
        if not optTargetDesc: return None
        targetRole = self.get_target_role(optLandingZone, targetAccountId)
        targetAccountName = optTargetDesc['Name']
        targetAccountEmail = optTargetDesc['Email']
        configRuleName = dispatch['configRuleNameBase']
        ruleCodeFolder = cfgrules.codeFolder(configRuleName, action, targetAccountName)
        if not ruleCodeFolder:
            report = {'Synopsis': "NoRuleImplementation", 'Dispatch': dispatch, 'AccountName': targetAccountName}
            logging.info(report)
            return None
        functionName = cfgCore.ruleFunctionName(ruleCodeFolder)
        acceptResource = filter.acceptResourceId(configRuleName, action, targetAccountName, resourceId)
        if not acceptResource:
            report = {'Synopsis': "ResourceExempt", 'Dispatch': dispatch, 'AccountName': targetAccountName}
            logging.info(report)
            return None

        det = {}
        det['awsAccountId'] = targetAccountId
        det['awsAccountName'] = targetAccountName
        det['awsAccountEmail'] = targetAccountEmail
        det['awsRegion'] = dispatch['awsRegion']
        det['roleName'] = targetRole
        det['resourceType'] = dispatch['resourceType']
        det['resourceId'] = resourceId
        target = DispatchEventTarget(det)
        de = {}
        de['configRuleName'] = configRuleName
        de['action'] = action
        de['conformancePackName'] = cfgrules.conformancePackName()
        de['preview'] = self.get_preview(configRuleName, action, targetAccountName)
        de['deploymentMethod'] = self.get_deployment_method(configRuleName, action, targetAccountName)
        de['manualTagName'] = self.get_manual_tag_name(configRuleName, action, targetAccountName)
        de['autoResourceTags'] = self.get_auto_resource_tags(configRuleName, action, targetAccountName)
        de['stackNamePattern'] = self.get_stack_name_pattern(configRuleName, action, targetAccountName)
        event = DispatchEvent(de, target)
        return {'functionName': functionName, 'event': event}

    def createInvokeList(self, dispatchList) -> List[RuleInvocation]:
        optLandingZone = self._discover.discoverLandingZone()
        invokeList = []
        for dispatch in dispatchList:
            optInvoke = self.create_invoke(optLandingZone, dispatch)
            if not optInvoke: continue
            invoke = RuleInvocation(optInvoke['functionName'], optInvoke['event'])
            invokeList.append(invoke)
        return invokeList

from typing import List, Set
import botocore, json

from lib.rdq import RdqError, RdqTimeout
from lib.rdq.base import ServiceUtils

class ResourceDescriptor:
    def __init__(self, resourceType, resourceId):
        self._resourceType = resourceType
        self._resourceId = resourceId

    @property
    def resourceType(self): return self._resourceType

    @property
    def resourceId(self): return self._resourceId

    def toDict(self) -> dict:
        return {
            'ResourceType': self._resourceType,
            'ResourceId': self._resourceId
        }

    def __str__(self):
        return json.dumps(self.toDict())

class RuleDescriptor:
    def __init__(self, configRuleName, accountId, awsRegion):
        self._configRuleName = configRuleName
        self._accountId = accountId
        self._awsRegion = awsRegion

    @property
    def configRuleName(self): return self._configRuleName

    @property
    def accountId(self): return self._accountId

    @property
    def awsRegion(self): return self._awsRegion

    def toDict(self) -> dict:
        return {
            'ConfigRuleName': self._configRuleName,
            'AccountId': self._accountId,
            'RegionName': self.awsRegion
        }

    def __str__(self):
        return json.dumps(self.toDict())

class AccountAgenda:
    def __init__(self, ruleDescriptors: List[RuleDescriptor]):
        mapAccount = {}
        for rd in ruleDescriptors:
            accountId = rd.accountId
            if not accountId in mapAccount:
                mapAccount[accountId] = {}
            mapRegion = mapAccount[accountId]
            region = rd.awsRegion
            if not region in mapRegion:
                mapRegion[region] = set()
            mapRegion[region].add(rd.configRuleName)
        self._mapAccount = mapAccount

    def accountIds(self) -> List[str]:
        return self._mapAccount.keys()

    def regionNames(self, accountId) -> List[str]:
        optMapRegion = self._mapAccount.get(accountId)
        if not optMapRegion: return []
        return optMapRegion.keys()

    def configRuleNameSet(self, accountId, regionName) -> Set[str]:
        optMapRegion = self._mapAccount.get(accountId)
        if not optMapRegion: return set()
        optRuleSet = optMapRegion.get(regionName)
        if not optRuleSet: return set()
        return optRuleSet



class CfgClient:
    def __init__(self, profile, maxAttempts=10):
        service = 'config'
        self._profile = profile
        self._client = profile.getClient(service)
        self._utils = ServiceUtils(profile, service, maxAttempts)

    def describe_rules(self, complianceTypes) -> List[RuleDescriptor]:
        accountId = self._profile.accountId
        awsRegion = self._profile.regionName
        op = 'describe_compliance_by_config_rule'
        try:
            paginator = self._client.get_paginator(op)
            page_iterator = paginator.paginate(
                ComplianceTypes=complianceTypes
                )
            results = []
            for page in page_iterator:
                items = page["ComplianceByConfigRules"]
                for item in items:
                    configRuleName = item.get('ConfigRuleName')
                    if not configRuleName: continue
                    results.append(RuleDescriptor(configRuleName, accountId, awsRegion))
            return results
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return []
            raise RdqError(self._utils.fail(e, op))

    def describe_aggregate_rules(self, aggregatorName, filters) -> List[RuleDescriptor]:
        op = 'describe_aggregate_compliance_by_config_rules'
        try:
            paginator = self._client.get_paginator(op)
            page_iterator = paginator.paginate(
                ConfigurationAggregatorName=aggregatorName,
                Filters=filters
                )
            results = []
            for page in page_iterator:
                items = page["AggregateComplianceByConfigRules"]
                for item in items:
                    configRuleName = item.get('ConfigRuleName')
                    if not configRuleName: continue
                    accountId = item.get('AccountId')
                    if not accountId: continue
                    awsRegion = item.get('AwsRegion')
                    if not awsRegion: continue
                    results.append(RuleDescriptor(configRuleName, accountId, awsRegion))
            return results
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return []
            raise RdqError(self._utils.fail(e, op, 'AggregatorName', aggregatorName))

    def get_resources_by_rule(self, ruleName, complianceType) -> List[ResourceDescriptor]:
        op = 'get_compliance_details_by_config_rule'
        try:
            paginator = self._client.get_paginator(op)
            page_iterator = paginator.paginate(
                ConfigRuleName=ruleName,
                ComplianceTypes=[complianceType]
                )
            results = []
            for page in page_iterator:
                items = page["EvaluationResults"]
                for item in items:
                    eri = item.get('EvaluationResultIdentifier')
                    if not eri: continue
                    erq = eri.get('EvaluationResultQualifier')
                    if not erq: continue
                    resourceType = erq.get('ResourceType')
                    if not resourceType: continue
                    resourceId = erq.get('ResourceId')
                    if not resourceId: continue
                    results.append(ResourceDescriptor(resourceType, resourceId))
            return results
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return []
            raise RdqError(self._utils.fail(e, op, 'RuleName', ruleName))

    def get_aggregate_resources_by_rule(self, aggregatorName, ruleName, accountId, awsRegion, complianceType) -> List[ResourceDescriptor]:
        op = 'get_aggregate_compliance_details_by_config_rule'
        try:
            paginator = self._client.get_paginator(op)
            page_iterator = paginator.paginate(
                ConfigurationAggregatorName=aggregatorName,
                ConfigRuleName=ruleName,
                AccountId=accountId,
                AwsRegion=awsRegion,
                ComplianceType=complianceType
                )
            results = []
            for page in page_iterator:
                items = page["AggregateEvaluationResults"]
                for item in items:
                    eri = item.get('EvaluationResultIdentifier')
                    if not eri: continue
                    erq = eri.get('EvaluationResultQualifier')
                    if not erq: continue
                    resourceType = erq.get('ResourceType')
                    if not resourceType: continue
                    resourceId = erq.get('ResourceId')
                    if not resourceId: continue
                    results.append(ResourceDescriptor(resourceType, resourceId))
            return results
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return []
            raise RdqError(self._utils.fail(e, op, 'AggregatorName', aggregatorName, 'RuleName', ruleName, 'AccountId', accountId))


    def selectNonCompliantAccountAgenda(self, aggregatorName=None) -> AccountAgenda:
        ruleDescriptors = []
        if aggregatorName is None:
            complianceTypes = ['NON_COMPLIANT']
            ruleDescriptors = self.describe_rules(complianceTypes)
        else:
            filters = { 'ComplianceType': 'NON_COMPLIANT' }
            ruleDescriptors = self.describe_aggregate_rules(aggregatorName, filters)
        return AccountAgenda(ruleDescriptors)
        
    def listNonCompliantResources(self, ruleName, aggregatorName=None, accountId=None, regionName=None) -> List[ResourceDescriptor]:
        complianceType = 'NON_COMPLIANT'
        if aggregatorName is None or accountId is None or regionName is None:
            return self.get_resources_by_rule(ruleName, complianceType)
        else:
            return self.get_aggregate_resources_by_rule(aggregatorName, ruleName, accountId, regionName, complianceType)

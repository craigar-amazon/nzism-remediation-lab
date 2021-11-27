import botocore
from lib.rdq import RdqError
from .base import ServiceUtils

def _match_target(rq, ex):
    if rq['Arn'] != ex['Arn']: return False
    if not ('RetryPolicy' in ex): return False
    rqRetryPolicy = rq['RetryPolicy']
    exRetryPolicy = ex['RetryPolicy']
    if not ('MaximumEventAgeInSeconds' in exRetryPolicy): return False
    if rqRetryPolicy['MaximumEventAgeInSeconds'] != exRetryPolicy['MaximumEventAgeInSeconds']: return False
    return True


class EventBridgeClient:
    def __init__(self, profile):
        service = 'events'
        self._profile = profile
        self._client = profile.getClient(service)
        self._utils = ServiceUtils(profile, service)

    def describe_event_bus(self, eventBusName):
        op = 'describe_event_bus'
        try:
            response = self._client.describe_event_bus(
                Name=eventBusName
            )
            return response
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return None
            raise RdqError(self._utils.fail(e, op, 'EventBusName', eventBusName))

    def create_event_bus_arn(self, eventBusName):
        op = 'create_event_bus'
        try:
            response = self._client.create_event_bus(
                Name=eventBusName
            )
            return response['EventBusArn']
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'EventBusName', eventBusName))

    def delete_event_bus(self, eventBusName):
        op = 'delete_event_bus'
        try:
            self._client.delete_event_bus(
                Name=eventBusName
            )
            return True
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return False
            raise RdqError(self._utils.fail(e, op, 'EventBusName', eventBusName))
    
    def put_permission(self, eventBusName, sid, action, condition):
        op = 'put_permission'
        try:
            self._client.put_permission(
                EventBusName=eventBusName,
                Principal = '*',
                Action = action,
                StatementId = sid,
                Condition = condition
            )
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'EventBusName', eventBusName, "Sid", sid))

    def list_rules(self, eventBusName):
        op = "list_rules"
        try:
            paginator = self._client.get_paginator(op)
            page_iterator = paginator.paginate(EventBusName=eventBusName)
            rules = []
            for page in page_iterator:
                items = page["Rules"]
                for item in items:
                    rules.append(item)
            return rules
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'EventBusName', eventBusName))

    def describe_rule(self, eventBusName, ruleName):
        op = 'describe_rule'
        try:
            response = self._client.describe_rule(
                EventBusName=eventBusName,
                Name=ruleName
            )
            return response
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return None
            raise RdqError(self._utils.fail(e, op, 'EventBusName', eventBusName, 'RuleName', ruleName))

    # Allow events:PutRule
    def put_rule_arn(self, eventBusName, ruleName, ruleDescription, eventPatternJson):
        op = 'put_rule'
        try:
            response = self._client.put_rule(
                EventBusName=eventBusName,
                Name=ruleName,
                Description=ruleDescription,
                EventPattern=eventPatternJson
            )
            return response['RuleArn']
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'EventBusName', eventBusName, 'RuleName', ruleName))

    def delete_rule(self, eventBusName, ruleName):
        op = 'delete_rule'
        try:
            self._client.delete_rule(
                EventBusName=eventBusName,
                Name=ruleName
            )
            return True
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return False
            raise RdqError(self._utils.fail(e, op, 'EventBusName', eventBusName, 'RuleName', ruleName))

    def list_targets_by_rule(self, eventBusName, ruleName):
        op = "list_targets_by_rule"
        try:
            paginator = self._client.get_paginator(op)
            page_iterator = paginator.paginate(EventBusName=eventBusName, Rule=ruleName)
            targets = []
            for page in page_iterator:
                items = page["Targets"]
                for item in items:
                    targets.append(item)
            return targets
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'EventBusName', eventBusName, 'RuleName', ruleName))

    def list_target_ids(self, eventBusName, ruleName):
        exTargets = self.list_targets_by_rule(eventBusName, ruleName)
        targetIds = []
        for target in exTargets:
            targetIds.append(target['Id'])
        return targetIds

    def find_target(self, eventBusName, ruleName, targetId):
        exTargets = self.list_targets_by_rule(eventBusName, ruleName)
        for target in exTargets:
            if target['Id'] == targetId:
                return target
        return None

    def put_targets(self, eventBusName, ruleName, targets):
        op = 'put_targets'
        try:
            self._client.put_targets(
                EventBusName=eventBusName,
                Rule=ruleName,
                Targets=targets
            )
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'EventBusName', eventBusName, 'RuleName', ruleName))

    def remove_targets(self, eventBusName, ruleName, targetIds):
        op = 'remove_targets'
        try:
            self._client.remove_targets(
                EventBusName=eventBusName,
                Rule=ruleName,
                Ids=targetIds
            )
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'EventBusName', eventBusName, 'RuleName', ruleName))

    def declareEventBusArn(self, eventBusName):
        exEventBus = self.describe_event_bus(eventBusName)
        if not exEventBus:
             return self.create_event_bus_arn(eventBusName)
        return exEventBus['Arn']

    def declareEventBusRuleArn(self, eventBusName, ruleName, ruleDescription, eventPatternMap):
        exRule = self.describe_rule(eventBusName, ruleName)
        reqd = {
            'Description': ruleDescription,
            'EventPattern': self._utils.to_json(eventPatternMap)
        }
        delta = False
        if exRule:
            ex = dict(exRule)
            ex['EventPattern'] = self._utils.to_json(exRule['EventPattern'])
            for rk in reqd:
                if reqd[rk] != ex[rk]:
                    delta = True
                    break
        else:
            delta = True
        if not delta: return exRule['Arn']
        return self.put_rule_arn(eventBusName, ruleName, reqd['Description'], reqd['EventPattern'])

    def declareEventBusTarget(self, eventBusName, ruleName, targetId, targetArn, maxAgeSeconds):        
        reqdTarget = {
            'Id': targetId,
            'Arn': targetArn,
            'RetryPolicy':  {
                'MaximumEventAgeInSeconds': maxAgeSeconds
            }
        }
        exTarget = self.find_target(eventBusName, ruleName, targetId)
        delta = False
        if exTarget:
            delta = not _match_target(reqdTarget, exTarget)
        else:
            delta = True
        if delta:
            self.put_targets(eventBusName, ruleName, [reqdTarget])
        return delta

    def declareEventBusPublishPermissionForAccount(self, eventBusName, accountId):
        sid = "pub-{}".format(accountId)
        action = 'events:PutEvents'
        condition = {
                'Type': 'StringEquals',
                'Key': 'aws:PrincipalAccount',
                'Value': accountId
        }
        self.put_permission(eventBusName, sid, action, condition)

    def declareEventBusPublishPermissionForOrganization(self, eventBusName, organizationId):
        sid = "pub-{}".format(organizationId)
        action = 'events:PutEvents'
        condition = {
                'Type': 'StringEquals',
                'Key': 'aws:PrincipalOrgID',
                'Value': organizationId
        }
        self.put_permission(eventBusName, sid, action, condition)


    def deleteEventBus(self, eventBusName):
        rules = self.list_rules(eventBusName)
        for rule in rules:
            ruleName = rule['Name']
            targetIds = self.list_target_ids(eventBusName, ruleName)
            self.remove_targets(eventBusName, ruleName, targetIds)
            self.delete_rule(eventBusName, ruleName)
        self.delete_event_bus(eventBusName)


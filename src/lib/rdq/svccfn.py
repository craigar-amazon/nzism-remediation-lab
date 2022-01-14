from typing import List
import botocore, json

from lib.base import Tags, DeltaBuild
from lib.rdq import RdqError, RdqTimeout
from lib.rdq.base import ServiceUtils

def _callAs(forOrganization):
    if forOrganization: return 'DELEGATED_ADMIN'
    return 'SELF'

def _matches(val, *args):
    for a in args:
        if a == val: return True
    return False

def _contains(val, *args):
    for a in args:
        if val.find(a) > 0: return True
    return False

class StackSetOperationRef:
    def __init__(self, stackSetId, operationId):
        self._stackSetId = stackSetId
        self._operationId = operationId

    @property
    def stackSetId(self): return self._stackSetId

    @property
    def operationId(self): return self._operationId

    def toDict(self) -> dict:
        return {
            'StackSetId': self.stackSetId,
            'OperationId': self._operationId  
        }

    def __str__(self):
        return json.dumps(self.toDict())


class StackSetOperation:
    def __init__(self, props):
        self._props = props

    @property
    def stackSetId(self): return self._props['StackSetId']

    @property
    def operationId(self): return self._props['OperationId']

    @property
    def action(self): return self._props['Action']

    @property
    def status(self): return self._props['Status']

    def toDict(self) -> dict:
        return self._props

    def __str__(self):
        return json.dumps(self._props)


class StackSummary:
    def __init__(self, props):
        self._props = props

    @property
    def stackId(self): return self._props['StackId']

    @property
    def status(self): return self._props.get('StackStatus')

    @property
    def statusReason(self): return self._props.get('StackStatusReason')

    @property
    def tags(self): return self._props.get('Tags')

    def toDict(self) -> dict:
        return self._props

    def __str__(self):
        return json.dumps(self._props)


class StackInstanceSummary:
    def __init__(self, props):
        self._props = props

    @property
    def stackSetId(self): return self._props['StackSetId']

    @property
    def region(self): return self._props['Region']

    @property
    def account(self): return self._props['Account']

    @property
    def stackId(self): return self._props.get('StackId')

    @property
    def status(self): return self._props.get('Status')

    @property
    def statusReason(self): return self._props.get('StatusReason')

    @property
    def stackInstanceStatus(self):
        siStatus = self._props.get('StackInstanceStatus')
        if not siStatus: return None
        return siStatus.get('DetailedStatus')

    @property
    def ouId(self): return self._props.get('OrganizationalUnitId')

    @property
    def driftStatus(self): return self._props.get('DriftStatus')

    def toDict(self) -> dict:
        return self._props

    def __str__(self):
        return json.dumps(self._props)


class CfnClient:
    def __init__(self, profile, maxAttempts=15):
        service = 'cloudformation'
        self._profile = profile
        self._client = profile.getClient(service)
        self._utils = ServiceUtils(profile, service, maxAttempts)


    def describe_stack(self, stackName) -> StackSummary:
        op = "describe_stacks"
        try:
            paginator = self._client.get_paginator(op)
            page_iterator = paginator.paginate(StackName=stackName)
            results = []
            for page in page_iterator:
                items = page["Stacks"]
                for item in items:
                    results.append(item)
            resultCount = len(results)
            if resultCount == 0: return None
            if resultCount == 1: return StackSummary(results[0])
            raise RdqError(self._utils.integrity("Multiple stacks for name", "StackName", stackName, "MatchCount", resultCount))
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return None
            if self._utils.is_error_code(e, 'ValidationError'): return None
            raise RdqError(self._utils.fail(e, op, 'StackName', stackName))

    def describe_stackset(self, stackSetName, callAs):
        op = 'describe_stack_set'
        try:
            response = self._client.describe_stack_set(
                StackSetName=stackSetName,
                CallAs=callAs
            )
            return response['StackSet']
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return None
            raise RdqError(self._utils.fail(e, op, 'StackSetName', stackSetName, 'CallAs', callAs))

    def describe_stackset_operation(self, stackSetName, callAs, operationId) -> StackSetOperation:
        op = 'describe_stack_set_operation'
        try:
            response = self._client.describe_stack_set_operation(
                StackSetName=stackSetName,
                OperationId=operationId,
                CallAs=callAs
            )
            return StackSetOperation(response['StackSetOperation'])
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return None
            raise RdqError(self._utils.fail(e, op, 'StackSetName', stackSetName, 'CallAs', callAs, 'OperationId', operationId))

    def list_stack_set_operations(self, stackSetName, callAs):
        op = "list_stack_set_operations"
        try:
            paginator = self._client.get_paginator(op)
            page_iterator = paginator.paginate(StackSetName=stackSetName, CallAs=callAs)
            results = []
            for page in page_iterator:
                items = page["Summaries"]
                for item in items:
                    results.append(item)
            return results
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return []
            raise RdqError(self._utils.fail(e, op, 'StackSetName', stackSetName, 'CallAs', callAs))

    def list_stack_instances(self, stackSetName, callAs) -> List[StackInstanceSummary]:
        op = "list_stack_instances"
        try:
            paginator = self._client.get_paginator(op)
            page_iterator = paginator.paginate(StackSetName=stackSetName, CallAs=callAs)
            results = []
            for page in page_iterator:
                items = page["Summaries"]
                for item in items:
                    results.append(StackInstanceSummary(item))
            return results
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return []
            raise RdqError(self._utils.fail(e, op, 'StackSetName', stackSetName, 'CallAs', callAs))

    def get_template(self, stackName):
        op = 'get_template'
        try:
            response = self._client.get_template(
                StackName=stackName
            )
            return response
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'StackName', stackName))

    #PREVIEW
    def create_stack_id(self, stackName, rq, tags):
        op = 'create_stack'
        args = {
            'StackName': stackName,
            'Configuration': rq,
            'Tags': tags.toDict()
        }
        if self._utils.preview(op, args): return None
        try:
            response = self._client.create_stack(
                StackName=stackName,
                TemplateBody=rq['TemplateBody'],
                Capabilities = rq['Capabilities'],
                Tags=tags.toList()
            )
            return response['StackId']
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'StackName', stackName))

    #PREVIEW
    def update_stack(self, stackName, rq, tags):
        op = 'update_stack'
        args = {
            'StackName': stackName,
            'NewConfiguration': rq,
            'Tags': tags.toDict()
        }
        if self._utils.preview(op, args): return
        try:
            self._client.update_stack(
                StackName=stackName,
                TemplateBody=rq['TemplateBody'],
                Capabilities = rq['Capabilities'],
                Tags=tags.toList()
            )
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'StackName', stackName))

    #PREVIEW
    def delete_stack(self, stackName):
        op = 'delete_stack'
        args = {
            'StackName': stackName
        }
        if self._utils.preview(op, args): return
        try:
            self._client.delete_stack(
                StackName=stackName
            )
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'StackName', stackName))


    def create_stackset_id(self, stackSetName, callAs, rq, tags):
        op = 'create_stack_set'
        try:
            response = self._client.create_stack_set(
                StackSetName=stackSetName,
                Description=rq['Description'],
                TemplateBody=rq['TemplateBody'],
                PermissionModel=rq['PermissionModel'],
                AutoDeployment=rq['AutoDeployment'],
                Capabilities=rq['Capabilities'],
                Tags=tags.toList(),
                CallAs=callAs
            )
            return response['StackSetId']
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'StackSetName', stackSetName, 'CallAs', callAs))

    def update_stackset_id(self, stackSetName, callAs, rq, tags):
        op = 'update_stack_set'
        operationId = self._utils.new_operation_id()
        tracker = self._utils.init_tracker(op, operationId)
        while True:
            try:
                self._client.update_stack_set(
                    StackSetName=stackSetName,
                    Description=rq['Description'],
                    TemplateBody=rq['TemplateBody'],
                    PermissionModel=rq['PermissionModel'],
                    AutoDeployment=rq['AutoDeployment'],
                    Capabilities = rq['Capabilities'],
                    Tags=tags.toList(),
                    OperationId=operationId,
                    CallAs=callAs
                )
                return operationId
            except botocore.exceptions.ClientError as e:
                if self._utils.retry_operation_in_progress(e, tracker):
                    tracker = self._utils.backoff(tracker)
                    continue
                raise RdqError(self._utils.fail(e, op, 'StackSetName', stackSetName, 'CallAs', callAs))

    def delete_stackset(self, stackSetName, callAs):
        op = 'delete_stack_set'
        tracker = self._utils.init_tracker(op)
        while True:
            try:
                self._client.delete_stack_set(
                    StackSetName=stackSetName,
                    CallAs=callAs
                )
                return True
            except botocore.exceptions.ClientError as e:
                if self._utils.is_resource_not_found(e): return False
                if self._utils.retry_operation_in_progress(e, tracker):
                    tracker = self._utils.backoff(tracker)
                    continue
                raise RdqError(self._utils.fail(e, op, 'StackSetName', stackSetName, 'CallAs', callAs))


    def create_stack_instances(self, stackSetName, callAs, orgunitids, regions):
        op = 'create_stack_instances'
        operationId = self._utils.new_operation_id()
        tracker = self._utils.init_tracker(op, operationId)
        while True:
            try:
                self._client.create_stack_instances(
                    StackSetName=stackSetName,
                    DeploymentTargets={
                        'OrganizationalUnitIds': orgunitids
                    },
                    Regions=regions,
                    OperationId=operationId,
                    CallAs=callAs
                )
                return operationId
            except botocore.exceptions.ClientError as e:
                if self._utils.retry_operation_in_progress(e, tracker):
                    tracker = self._utils.backoff(tracker)
                    continue
                raise RdqError(self._utils.fail(e, op, 'StackSetName', stackSetName, 'CallAs', callAs, 'OrgUnitIds', orgunitids))

    def delete_stack_instances(self, stackSetName, callAs, ouSet, accountSet, regionSet):
        op = 'delete_stack_instances'
        operationId = self._utils.new_operation_id()
        regions = list(regionSet)
        deploymentTargets = {}
        if len(ouSet) > 0:
            deploymentTargets['OrganizationalUnitIds'] = list(ouSet)
        else:
            deploymentTargets['Accounts'] = list(accountSet)
        tracker = self._utils.init_tracker(op, operationId)
        while True:
            try:
                self._client.delete_stack_instances(
                    StackSetName=stackSetName,
                    DeploymentTargets=deploymentTargets,
                    Regions=regions,
                    RetainStacks = False,
                    OperationId = operationId,
                    CallAs=callAs
                )
                return operationId
            except botocore.exceptions.ClientError as e:
                if self._utils.is_resource_not_found(e): return None
                if self._utils.retry_operation_in_progress(e, tracker):
                    tracker = self._utils.backoff(tracker)
                    continue
                raise RdqError(self._utils.fail(e, op, 'StackSetName', stackSetName, 'CallAs', callAs, 'OrgUnitIds', ouSet))

    def get_completed_stack(self, stackName, maxSecs) -> StackSummary:
        op = 'AwaitStackCompletion'
        tracker = self._utils.init_tracker(op, maxSecs=maxSecs, policy="ElapsedOnly")
        while True:
            stack = self.describe_stack(stackName)
            if not stack:
                return None
            status = stack.status
            if not _contains(status, '_IN_PROGRESS'):
                return stack
            self._utils.info(op, 'StackName', stackName, "Waiting for Completion", "Status", status)
            if self._utils.retry(tracker):
                tracker = self._utils.backoff(tracker, 30)
                continue
            return None

    def is_running_stack_set_operations(self, stackSetName, callAs, maxSecs):
        op = 'AwaitRunningStackSetOperations'
        tracker = self._utils.init_tracker(op, maxSecs=maxSecs, policy="ElapsedOnly")
        while True:
            operations = self.list_stack_set_operations(stackSetName, callAs)
            waitCount = 0
            for operation in operations:
                status = operation['Status']
                if _matches(status, 'RUNNING', 'STOPPING', 'QUEUED'):
                    self._utils.info(op, 'StackSetName', stackSetName, "Waiting for Operation", "Operation", operation)
                    waitCount = waitCount + 1
            if waitCount == 0:
                return False
            if self._utils.retry(tracker):
                tracker = self._utils.backoff(tracker, 120)
                continue
            return True

    def wait_on_running_stack(self, stackName, maxSecs) -> StackSummary:
        op = 'WaitForRunningStack'
        completedStack = self.get_completed_stack(stackName, maxSecs)
        if completedStack: return completedStack
        raise RdqTimeout(self._utils.expired(op, 'StackName', stackName, 'MaxSecs', maxSecs))

    def wait_on_running_stack_set_operations(self, stackSetName, callAs, maxSecs):
        op = 'WaitForRunningStackSetOperations'
        isRunning = self.is_running_stack_set_operations(stackSetName, callAs, maxSecs)
        if isRunning:
            raise RdqTimeout(self._utils.expired(op, 'StackSetName', stackSetName, 'MaxSecs', maxSecs))

    #PREVIEW
    def declareStack(self, stackName, templateMap, tags):
        db = DeltaBuild()
        db.putRequiredJson('TemplateBody', templateMap)
        db.putRequiredList('Capabilities', ['CAPABILITY_NAMED_IAM'])
        rq = db.required()
        ex = self.describe_stack(stackName)
        if ex:
            stackId = ex.stackId
            db.loadExisting(ex)
            exTemplate = self.get_template(stackName)
            db.loadExisting(exTemplate)
            db.normaliseExistingJson('TemplateBody')
            db.normaliseExistingList('Capabilities')
            delta = db.delta()
            exTags = Tags(ex.tags)
            deltaTags = tags.subtract(exTags)
            if len(delta) > 0 or deltaTags.notEmpty():
                self.wait_on_running_stack(stackName, 120)
                self.update_stack(stackName, rq, tags)
        else:
            stackId = self.create_stack_id(stackName, rq, tags)
        return stackId

    #PREVIEW
    def removeStack(self, stackName):
        self.get_completed_stack(stackName, 600)
        self.delete_stack(stackName)

    def getStack(self, stackName) -> StackSummary:
        return self.describe_stack(stackName)

    def getCompletedStack(self, stackName, maxSecs=600) -> StackSummary:
        return self.get_completed_stack(stackName, maxSecs)


    def declareStackSet(self, stackSetName, templateMap, description, tags, orgunitids, regions, forOrganization=True) -> StackSetOperationRef:
        callAs = _callAs(forOrganization)
        db = DeltaBuild()
        db.putRequired('Description', description)
        db.putRequiredJson('TemplateBody', templateMap)
        db.putRequired('PermissionModel', 'SERVICE_MANAGED')
        db.putRequired('AutoDeployment.Enabled', True)
        db.putRequired('AutoDeployment.RetainStacksOnAccountRemoval', True)
        db.putRequiredList('Capabilities', ['CAPABILITY_NAMED_IAM'])
        rq = db.required()
        ex = self.describe_stackset(stackSetName, callAs)
        if ex:
            stacksetId = ex['StackSetId']
            db.loadExisting(ex)
            db.normaliseExistingJson('TemplateBody')
            db.normaliseExistingList('Capabilities')
            delta = db.delta()
            exTags = Tags(ex.get('Tags'))
            deltaTags = tags.subtract(exTags)
            if len(delta) > 0 or deltaTags.notEmpty():
                op = 'ApplyStackSetDelta'
                self._utils.info(op, 'StackSetName', stackSetName, "Updating Stack Set", "Delta", delta)
                if self.is_running_stack_set_operations(stackSetName, callAs, 600):
                    self._utils.warning(op, 'StackSetName', stackSetName, "Previous Stack Set Operations Still Running", "Delta", delta)
                operationId = self.update_stackset_id(stackSetName, callAs, rq, tags)
            else:
                operationId = None
        else:
            self.wait_on_running_stack_set_operations(stackSetName, callAs, 600)
            stacksetId = self.create_stackset_id(stackSetName, callAs, rq, tags)
            self.wait_on_running_stack_set_operations(stackSetName, callAs, 600)
            operationId = self.create_stack_instances(stackSetName, callAs, orgunitids, regions)
        return StackSetOperationRef(stacksetId, operationId)

    def removeStackSet(self, stackSetName, forOrganization=True):
        callAs = _callAs(forOrganization)
        ouSet = set()
        accountSet = set()
        regionSet = set()
        stackInstances = self.list_stack_instances(stackSetName, callAs)
        for stackInstance in stackInstances:
            regionSet.add(stackInstance.region)
            if stackInstance.ouId:
                ouSet.add(stackInstance.ouId)
            else:
                accountSet.add(stackInstance.account)
        operationId = None
        if len(regionSet) > 0 and (len(ouSet) > 0 or len(accountSet) > 0):
            operationId = self.delete_stack_instances(stackSetName, callAs, ouSet, accountSet, regionSet)
            self.is_running_stack_set_operations(stackSetName, callAs, 600)
        self.delete_stackset(stackSetName, callAs)
        return operationId

    def getStackSetOperation(self, stackSetName, operationId, forOrganization=True) -> StackSetOperation:
        callAs = _callAs(forOrganization)
        return self.describe_stackset_operation(stackSetName, callAs, operationId)

    def listStackInstances(self, stackSetName, forOrganization=True) -> List[StackInstanceSummary]:
        callAs = _callAs(forOrganization)
        return self.list_stack_instances(stackSetName, callAs)

    def isRunningStackSetOperations(self, stackSetName, maxSecs=300, forOrganization=True):
        callAs = _callAs(forOrganization)
        return self.is_running_stack_set_operations(stackSetName, callAs, maxSecs)


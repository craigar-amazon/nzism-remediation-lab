import botocore

from lib.base import DeltaBuild
from lib.rdq import RdqError
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


class CfnClient:
    def __init__(self, profile, maxAttempts=15):
        service = 'cloudformation'
        self._profile = profile
        self._client = profile.getClient(service)
        self._utils = ServiceUtils(profile, service, maxAttempts)


    def describe_stack(self, stackName):
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
            if resultCount == 1: return results[0]
            raise RdqError(self._utils.integrity("Multiple stacks for name", "StackName", stackName, "MatchCount", resultCount))
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return None
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

    def describe_stackset_operation(self, stackSetName, callAs, operationId):
        op = 'describe_stack_set_operation'
        try:
            response = self._client.describe_stack_set_operation(
                StackSetName=stackSetName,
                OperationId=operationId,
                CallAs=callAs
            )
            return response['StackSetOperation']
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
    def create_stack_id(self, stackName, rq):
        op = 'create_stack'
        args = {
            'StackName': stackName,
            'Configuration': rq
        }
        if self._utils.preview(op, args): return None
        try:
            response = self._client.create_stack(
                StackName=stackName,
                TemplateBody=rq['TemplateBody'],
                Capabilities = rq['Capabilities']
            )
            return response['StackId']
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'StackName', stackName))

    #PREVIEW
    def update_stack(self, stackName, rq):
        op = 'update_stack'
        args = {
            'StackName': stackName,
            'NewConfiguration': rq
        }
        if self._utils.preview(op, args): return
        try:
            self._client.update_stack(
                StackName=stackName,
                TemplateBody=rq['TemplateBody'],
                Capabilities = rq['Capabilities']
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


    def create_stackset_id(self, stackSetName, callAs, rq):
        op = 'create_stack_set'
        try:
            response = self._client.create_stack_set(
                StackSetName=stackSetName,
                Description=rq['Description'],
                TemplateBody=rq['TemplateBody'],
                PermissionModel=rq['PermissionModel'],
                AutoDeployment=rq['AutoDeployment'],
                Capabilities = rq['Capabilities'],
                CallAs=callAs
            )
            return response['StackSetId']
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'StackSetName', stackSetName, 'CallAs', callAs))

    def update_stackset_id(self, stackSetName, callAs, rq):
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

    def delete_stack_instances(self, stackSetName, callAs, orgunitids, regions):
        op = 'delete_stack_instances'
        operationId = self._utils.new_operation_id()
        tracker = self._utils.init_tracker(op, operationId)
        while True:
            try:
                self._client.delete_stack_instances(
                    StackSetName=stackSetName,
                    DeploymentTargets={
                        'OrganizationalUnitIds': orgunitids
                    },
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
                raise RdqError(self._utils.fail(e, op, 'StackSetName', stackSetName, 'CallAs', callAs, 'OrgUnitIds', orgunitids))

    def get_completed_stack(self, stackName, maxSecs):
        op = 'AwaitStackComplation'
        tracker = self._utils.init_tracker(op, maxSecs=maxSecs, policy="ElapsedOnly")
        while True:
            stack = self.describe_stack(stackName)
            status = stack['StackStatus']
            if not _contains(status, '_IN_PROGRESS'):
                return stack
            self._utils.info(op, 'StackName', stackName, "Waiting for Completion", "Status", status)
            if self._utils.retry(tracker):
                tracker = self._utils.backoff(tracker, 120)
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

    def wait_on_running_stack(self, stackName, maxSecs):
        op = 'WaitForRunningStack'
        runningStatus = self.get_completed_stack(stackName, maxSecs)
        if runningStatus:
            raise RdqError(self._utils.expired(op, 'StackName', stackName, 'Status', runningStatus, 'MaxSecs', maxSecs))

    def wait_on_running_stack_set_operations(self, stackSetName, callAs, maxSecs):
        op = 'WaitForRunningStackSetOperations'
        isRunning = self.is_running_stack_set_operations(stackSetName, callAs, maxSecs)
        if isRunning:
            raise RdqError(self._utils.expired(op, 'StackSetName', stackSetName, 'MaxSecs', maxSecs))

    #PREVIEW
    def declareStack(self, stackName, templateMap):
        db = DeltaBuild()
        db.putRequiredJson('TemplateBody', templateMap)
        db.putRequiredList('Capabilities', ['CAPABILITY_NAMED_IAM'])
        rq = db.required()
        ex = self.describe_stack(stackName)
        if ex:
            stackId = ex['StackId']
            db.loadExisting(ex)
            exTemplate = self.get_template(stackName)
            db.loadExisting(exTemplate)
            db.normaliseExistingJson('TemplateBody')
            db.normaliseExistingList('Capabilities')
            delta = db.delta()
            if delta:
                self.wait_on_running_stack(stackName, 120)
                self.update_stack(stackName, rq)
        else:
            self.wait_on_running_stack(stackName, 120)
            stackId = self.create_stack_id(stackName, rq)
        return stackId

    #PREVIEW
    def deleteStack(self, stackName):
        self.get_completed_stack(stackName, 600)
        self.delete_stack(stackName)

    def getCompletedStack(self, stackName, maxSecs=120):
        return self.get_completed_stack(stackName, maxSecs)


    def declareStackSet(self, stackSetName, templateMap, stackSetDescription, orgunitids, regions, forOrganization=True):
        callAs = _callAs(forOrganization)
        db = DeltaBuild()
        db.putRequired('Description', stackSetDescription)
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
            if delta:
                op = 'ApplyStackSetDelta'
                self._utils.info(op, 'StackSetName', stackSetName, "Updating Stack Set", "Delta", delta)
                if self.is_running_stack_set_operations(stackSetName, callAs, 600):
                    self._utils.warning(op, 'StackSetName', stackSetName, "Previous Stack Set Operations Still Running", "Delta", delta)
                operationId = self.update_stackset_id(stackSetName, callAs, rq)
            else:
                operationId = None
        else:
            self.wait_on_running_stack_set_operations(stackSetName, callAs, 600)
            stacksetId = self.create_stackset_id(stackSetName, callAs, rq)
            self.wait_on_running_stack_set_operations(stackSetName, callAs, 600)
            operationId = self.create_stack_instances(stackSetName, callAs, orgunitids, regions)
        return {
            'StackSetId': stacksetId,
            'OperationId': operationId
        }

    def deleteStackSet(self, stackSetName, orgunitids, regions, forOrganization=True):
        callAs = _callAs(forOrganization)
        operationId = self.delete_stack_instances(stackSetName, callAs, orgunitids, regions)
        self.is_running_stack_set_operations(stackSetName, callAs, 600)
        self.delete_stackset(stackSetName, callAs)
        return operationId

    def getStackSetOperation(self, stackSetName, operationId, forOrganization=True):
        callAs = _callAs(forOrganization)
        return self.describe_stackset_operation(stackSetName, callAs, operationId)

    def isRunningStackSetOperations(self, stackSetName, maxSecs=300, forOrganization=True):
        callAs = _callAs(forOrganization)
        return self.is_running_stack_set_operations(stackSetName, callAs, maxSecs)

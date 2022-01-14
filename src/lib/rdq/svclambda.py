import hashlib
import base64
import botocore

from lib.base import Tags, DeltaBuild
from lib.rdq import RdqError
from lib.rdq.base import ServiceUtils

def _codeSha256(codeZip):
    hash = hashlib.sha256()
    hash.update(codeZip)
    return base64.b64encode(hash.digest()).decode()

_UndefinedConcurrency = -1

class LambdaClient:
    def __init__(self, profile, maxAttempts=10):
        service = 'lambda'
        self._profile = profile
        self._client = profile.getClient(service)
        self._utils = ServiceUtils(profile, service, maxAttempts)

    # Allow lambda:GetFunction
    def get_function(self, functionName):
        op = 'get_function'
        try:
            response = self._client.get_function(
                FunctionName=functionName
            )
            return response
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return None
            raise RdqError(self._utils.fail(e, op, 'FunctionName', functionName))

    def get_function_nonpending(self, functionName):
        op = "WaitForStateTransition"
        tracker = self._utils.init_tracker(op)
        while True:
            exFunction = self.get_function(functionName)
            if not exFunction: return None
            fc = exFunction['Configuration']
            state = fc['State']
            lastUpdateStatus = fc.get('LastUpdateStatus')
            stateReason = fc.get('StateReason')
            self._utils.info(op, 'FunctionName', functionName, "Checking function state", "State", state, "LastUpdateStatus", lastUpdateStatus, "StateReason", stateReason)
            retry = (state == 'Pending') or (lastUpdateStatus == 'InProgress')
            if not retry: return exFunction
            if self._utils.retry(tracker):
                tracker = self._utils.backoff(tracker)

    def get_function_concurrency(self, functionArn):
        op = 'get_function_concurrency'
        try:
            response = self._client.get_function_concurrency(
                FunctionName=functionArn
            )
            return response.get('ReservedConcurrentExecutions', _UndefinedConcurrency)
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return -1
            raise RdqError(self._utils.fail(e, op, 'FunctionArn', functionArn))

    # Allow lambda:CreateFunction
    def create_function(self, functionName, rq, codeZip, tags):
        op = 'create_function'
        tracker = self._utils.init_tracker(op)
        while True:
            try:
                response = self._client.create_function(
                    FunctionName=functionName,
                    Runtime=rq['Runtime'],
                    Role=rq['Role'],
                    Handler=rq['Handler'],
                    Description=rq['Description'],
                    Timeout=rq['Timeout'],
                    MemorySize=rq['MemorySize'],
                    Environment=rq['Environment'],
                    Code={
                        'ZipFile': codeZip
                    },
                    Tags=tags.toDict()
                )
                return response
            except botocore.exceptions.ClientError as e:
                if self._utils.retry_propagation_delay(e, tracker):
                    tracker = self._utils.backoff(tracker)
                    continue
                raise RdqError(self._utils.fail(e, op, 'FunctionName', functionName, 'RoleArn', rq['Role'], 'Tracker', tracker))

    # Allow lambda:UpdateFunctionConfiguration
    def update_function_configuration(self, functionName, rq):
        op = 'update_function_configuration'
        tracker = self._utils.init_tracker(op)
        while True:
            try:
                response = self._client.update_function_configuration(
                    FunctionName=functionName,
                    Runtime=rq['Runtime'],
                    Role=rq['Role'],
                    Handler=rq['Handler'],
                    Description=rq['Description'],
                    Timeout=rq['Timeout'],
                    MemorySize=rq['MemorySize'],
                    Environment=rq['Environment']
                )
                return response
            except botocore.exceptions.ClientError as e:
                if self._utils.retry_propagation_delay(e, tracker):
                    tracker = self._utils.backoff(tracker)
                    continue
                if self._utils.retry_resource_conflict(e, tracker):
                    tracker = self._utils.backoff(tracker)
                    continue
                raise RdqError(self._utils.fail(e, op, 'FunctionName', functionName, 'RoleArn', rq['Role'], 'Tracker', tracker))

    # Allow lambda:UpdateFunctionCode
    def update_function_code(self, functionName, codeZip):
        op = 'update_function_code'
        tracker = self._utils.init_tracker(op)
        while True:
            try:
                response = self._client.update_function_code(
                    FunctionName=functionName,
                    ZipFile=codeZip
                )
                return response
            except botocore.exceptions.ClientError as e:
                if self._utils.retry_resource_conflict(e, tracker):
                    tracker = self._utils.backoff(tracker)
                    continue
                raise RdqError(self._utils.fail(e, op, 'FunctionName', functionName))

    def put_function_concurrency(self, functionArn, reservedConcurrentExecutions: int):
        op = 'put_function_concurrency'
        if reservedConcurrentExecutions == _UndefinedConcurrency: return False
        try:
            self._client.put_function_concurrency(
                FunctionName=functionArn,
                ReservedConcurrentExecutions = reservedConcurrentExecutions
            )
            return True
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'FunctionArn', functionArn, 'ReservedConcurrentExecutions', reservedConcurrentExecutions))

    def get_policy(self, functionArn):
        op = 'get_policy'
        try:
            response = self._client.get_policy(
                FunctionName=functionArn
            )
            return response
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return None
            raise RdqError(self._utils.fail(e, op, 'FunctionArn', functionArn))

    def add_permission(self, functionArn, sid, action, principal, sourceArn):
        op = 'add_permission'
        try:
            self._client.add_permission(
                FunctionName=functionArn,
                StatementId = sid,
                Action = action,
                Principal = principal,
                SourceArn = sourceArn
            )
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'FunctionArn', functionArn, 'Principal', principal))

    def remove_permission(self, functionArn, sid):
        op = 'remove_permission'
        try:
            self._client.remove_permission(
                FunctionName=functionArn,
                StatementId = sid
            )
            return True
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return False
            raise RdqError(self._utils.fail(e, op, 'FunctionArn', functionArn, 'Sid', sid))


    # Allow lambda:DeleteFunction
    def delete_function(self, functionName):
        op ='delete_function'
        try:
            self._client.delete_function(
                FunctionName=functionName
            )
            return True
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return False
            raise RdqError(self._utils.fail(e, op, 'FunctionName', functionName))

    def list_event_source_mappings(self, functionName, eventSourceArn):
        op = "list_event_source_mappings"
        try:
            paginator = self._client.get_paginator(op)
            page_iterator = paginator.paginate(FunctionName=functionName, EventSourceArn=eventSourceArn)
            mappings = []
            for page in page_iterator:
                items = page["EventSourceMappings"]
                for item in items:
                    mappings.append(item)
            return mappings
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'FunctionName', functionName, 'EventSourceArn', eventSourceArn))

    def list_event_source_mappings_all(self, functionName):
        op = "list_event_source_mappings"
        try:
            paginator = self._client.get_paginator(op)
            page_iterator = paginator.paginate(FunctionName=functionName)
            mappings = []
            for page in page_iterator:
                items = page["EventSourceMappings"]
                for item in items:
                    mappings.append(item)
            return mappings
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'FunctionName', functionName))

    def get_event_source_mapping(self, uuid):
        op = 'get_event_source_mapping'
        try:
            response = self._client.get_event_source_mapping(
                UUID=uuid
            )
            return response
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'UUID', uuid))

    def find_event_source_mapping(self, functionName, eventSourceArn):
        mappings = self.list_event_source_mappings(functionName, eventSourceArn)
        mappingCount = len(mappings)
        if mappingCount == 0: return None
        if mappingCount > 1:
            msg = "Multiple ({}) event source mappings".format(mappingCount)
            raise RdqError(self._utils.integrity(msg, 'FunctionName', functionName, 'EventSourceArn', eventSourceArn))
        mapping = mappings[0]
        uuid = mapping['UUID']
        return self.get_event_source_mapping(uuid)

    def create_event_source_mapping_uuid(self, functionName, eventSourceArn, cfg):
        op = 'create_event_source_mapping'
        try:
            response = self._client.create_event_source_mapping(
                FunctionName=functionName,
                EventSourceArn=eventSourceArn,
                BatchSize=cfg['BatchSize'],
                MaximumBatchingWindowInSeconds=cfg['MaximumBatchingWindowInSeconds'],
                Enabled=True
            )
            return response['UUID']
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'FunctionName', functionName, 'EventSourceArn', eventSourceArn))

    def update_event_source_mapping(self, uuid, cfg):
        op = 'update_event_source_mapping'
        try:
            self._client.update_event_source_mapping(
                UUID=uuid,
                BatchSize=cfg['BatchSize'],
                MaximumBatchingWindowInSeconds=cfg['MaximumBatchingWindowInSeconds']
            )
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'UUID', uuid))

    def enable_event_source_mapping_for_uuid(self, uuid, enabled):
        op = 'update_event_source_mapping'
        try:
            self._client.update_event_source_mapping(
                UUID=uuid,
                Enabled=enabled
            )
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'UUID', uuid))

    def enable_event_source_mappings(self, mappings, enabled):
        for mapping in mappings:
            uuid = mapping['UUID']
            self.enable_event_source_mapping_for_uuid(uuid, enabled)

    def delete_event_source_mappings(self, mappings):
        for mapping in mappings:
            uuid = mapping['UUID']
            self.delete_event_source_mapping_for_uuid(uuid)

    def delete_event_source_mapping_for_uuid(self, uuid):
        op = 'delete_event_source_mapping'
        tracker = self._utils.init_tracker(op)
        while True:
            try:
                self._client.delete_event_source_mapping(
                    UUID=uuid
                )
                return
            except botocore.exceptions.ClientError as e:
                if self._utils.is_resource_not_found(e): return
                if self._utils.retry_resource_in_use(e, tracker):
                    tracker = self._utils.backoff(tracker)
                    continue
                raise RdqError(self._utils.fail(e, op, 'UUID', uuid))


    # Allow lambda:InvokeFunction
    def invoke_function_json(self, functionName, payloadMap):
        op = 'invoke'
        inJson = self._utils.to_json(payloadMap)
        inBytes = inJson.encode("utf-8")
        try:
            response = self._client.invoke(
                FunctionName=functionName,
                InvocationType='RequestResponse',
                Payload=inBytes
            )
            outBytes = response['Payload'].read()
            outJson = outBytes.decode("utf-8")
            outMap = self._utils.from_json(outJson)
            return {
                'StatusCode': response['StatusCode'],
                'Payload': outMap
            }
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'FunctionName', functionName))

    def declareFunctionArn(self, functionName, description, roleArn, cfg: dict, concurrency: dict, codeZip, tags: Tags):
        dbCfg = DeltaBuild()
        dbCfg.putRequired('Handler', 'lambda_function.lambda_handler')
        dbCfg.putRequired('Environment.Variables.LOGLEVEL', 'INFO')
        dbCfg.updateRequired(cfg)
        dbCfg.putRequired('Description', description)
        dbCfg.putRequired('Role', roleArn)
        rqCfg = dbCfg.required()
        rqReservedConcurrentExecutions = concurrency.get('ReservedConcurrentExecutions', _UndefinedConcurrency)
        exFunction = self.get_function(functionName)
        if not exFunction:
            newFunction = self.create_function(functionName, rqCfg, codeZip, tags)
            self.get_function_nonpending(functionName)
            self.put_function_concurrency(functionName, rqReservedConcurrentExecutions)
            return newFunction['FunctionArn']
        exFunctionConfiguration = exFunction['Configuration']
        exFunctionArn = exFunctionConfiguration['FunctionArn']
        dbCfg.loadExisting(exFunctionConfiguration)
        delta = dbCfg.delta()
        if delta:
            self._utils.info('CheckConfigurationDelta', 'FunctionName', functionName, "Reconfiguring", "Delta", delta)
            self.update_function_configuration(functionName, rqCfg)
            self.get_function_nonpending(functionName)        
        exCodeSha256 = exFunctionConfiguration['CodeSha256']
        inCodeSha256 = _codeSha256(codeZip)
        if inCodeSha256 != exCodeSha256:
            self.update_function_code(functionName, codeZip)
            self.get_function_nonpending(functionName)
        else:
            self._utils.info('CheckCodeSHA256', 'FunctionName', functionName, "Code unchanged", "CodeSHA256", exCodeSha256)
        exReservedConcurrentExecutions = self.get_function_concurrency(functionName)
        if exReservedConcurrentExecutions != rqReservedConcurrentExecutions:
            self.put_function_concurrency(functionName, rqReservedConcurrentExecutions)
        exTags = Tags(exFunction['Tags'], functionName)
        self._utils.declare_tags(exFunctionArn, tags, exTags)
        return exFunctionArn

    def declareInvokePermission(self, functionArn, sid, principal, sourceArn):
        action = "lambda:InvokeFunction"
        self.remove_permission(functionArn, sid)
        self.add_permission(functionArn, sid, action, principal, sourceArn)

    def removeFunction(self, functionName):
        return self.delete_function(functionName)

    def declareEventSourceMappingUUID(self, functionName, eventSourceArn, cfg):
        exMapping = self.find_event_source_mapping(functionName, eventSourceArn)
        if not exMapping:
            return self.create_event_source_mapping_uuid(functionName, eventSourceArn, cfg)
        uuid = exMapping['UUID']
        anames = ['BatchSize', 'MaximumBatchingWindowInSeconds']
        delta = False
        for aname in anames:
            rq = cfg[aname]
            ex = exMapping[aname]
            if rq != ex:
                delta = True
                break
        if delta:
            self.update_event_source_mapping(uuid, cfg)
        return uuid

    def enableEventSourceMappingsForFunction(self, functionName, isEnabled):
        mappings = self.list_event_source_mappings_all(functionName)
        self.enable_event_source_mappings(mappings, isEnabled)

    def removeEventSourceMapping(self, functionName, eventSourceArn):
        exMapping = self.find_event_source_mapping(functionName, eventSourceArn)
        if not exMapping: return False
        uuid = exMapping['UUID']
        self.delete_event_source_mapping_for_uuid(uuid)
        return True

    def removeEventSourceMappingsForFunction(self, functionName):
        mappings = self.list_event_source_mappings_all(functionName)
        self.delete_event_source_mappings(mappings)

    def invokeFunctionJson(self, functionName, payloadMap):
        return self.invoke_function_json(functionName, payloadMap)


import botocore

from .base import ServiceUtils

class LambdaClient:
    def __init__(self, profile, maxAttempts=10):
        service = 'lambda'
        self._profile = profile
        self._client = profile.getClient(service)
        self._utils = ServiceUtils(service, maxAttempts)

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
            raise Exception(self._utils.fail(e, op, 'FunctionName', functionName))

    # Allow lambda:CreateFunction
    def create_function(self, functionName, functionDescription, roleArn, cfg, codeZip):
        op = 'create_function'
        tracker = self._utils.init_tracker()
        while True:
            try:
                response = self._client.create_function(
                    FunctionName=functionName,
                    Runtime=cfg['Runtime'],
                    Role=roleArn,
                    Handler=cfg['Handler'],
                    Description=functionDescription,
                    Timeout=cfg['Timeout'],
                    MemorySize=cfg['MemorySize'],
                    Code={
                        'ZipFile': codeZip
                    }
                )
                return response
            except botocore.exceptions.ClientError as e:
                if self._utils.retry_propagation_delay(e, tracker):
                    tracker = self._utils.backoff(tracker)
                    continue
                raise Exception(self._utils.fail(e, op, 'FunctionName', functionName, 'RoleArn', roleArn, 'Tracker', tracker))

    # Allow lambda:UpdateFunctionConfiguration
    def update_function_configuration(self, functionName, functionDescription, roleArn, cfg):
        op = 'update_function_configuration'
        while True:
            try:
                response = self._client.update_function_configuration(
                    FunctionName=functionName,
                    Runtime=cfg['Runtime'],
                    Role=roleArn,
                    Handler=cfg['Handler'],
                    Description=functionDescription,
                    Timeout=cfg['Timeout'],
                    MemorySize=cfg['MemorySize']
                )
                return response
            except botocore.exceptions.ClientError as e:
                if self._utils.retry_propagation_delay(e, tracker):
                    tracker = self._utils.backoff(tracker)
                    continue
                raise Exception(self._utils.fail(e, op, 'FunctionName', functionName, 'RoleArn', roleArn, 'Tracker', tracker))

    # Allow lambda:UpdateFunctionCode
    def update_function_code(self, functionName, codeZip):
        op = 'update_function_code'
        try:
            response = self._client.update_function_code(
                FunctionName=functionName,
                ZipFile=codeZip
            )
            return response
        except botocore.exceptions.ClientError as e:
            raise Exception(self._utils.fail(e, op, 'FunctionName', functionName))


    def get_policy(self, functionArn):
        op = 'get_policy'
        try:
            response = self._client.get_policy(
                FunctionName=functionArn
            )
            return response
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return None
            raise Exception(self._utils.fail(e, op, 'FunctionArn', functionArn))

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
            raise Exception(self._utils.fail(e, op, 'FunctionArn', functionArn, 'Principal', principal))

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
            raise Exception(self._utils.fail(e, op, 'FunctionArn', functionArn, 'Sid', sid))


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
            raise Exception(self._utils.fail(e, op, 'FunctionName', functionName))

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
            self._utils.fail(e, op, 'FunctionName', functionName)
            return None


    def declareFunctionArn(self, functionName, functionDescription, roleArn, cfg, codeZip):
        exFunction = self.get_function(functionName)
        if not exFunction:
            newFunction = self.create_function(functionName, functionDescription, roleArn, cfg, codeZip)
            return newFunction['FunctionArn']
        self.update_function_configuration(functionName, functionDescription, roleArn, cfg)
        self.update_function_code(functionName, codeZip)
        return exFunction['Configuration']['FunctionArn']

    def declareInvokePermission(self, functionArn, sid, principal, sourceArn):
        action = "lambda:InvokeFunction"
        self.remove_permission(functionArn, sid)
        self.add_permission(functionArn, sid, action, principal, sourceArn)

    def deleteFunction(self, functionName):
        return self.delete_function(functionName)

    def invokeFunctionJson(self, functionName, payloadMap):
        return self.invoke_function_json(functionName, payloadMap)


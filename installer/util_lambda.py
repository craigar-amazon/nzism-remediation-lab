import json
import botocore

from util_file import getZipCodeBytes

def _is_resource_not_found(e):
    return e.response['Error']['Code'] == 'ResourceNotFoundException'    

def _fail(e, op, functionName):
    print("Unexpected error calling lambda."+op)
    print("functionName: "+functionName)
    print(e)
    return "Unexpected error calling {} on {}".format(op, functionName)

# Allow lambda:GetFunction
def getLambdaFunction(ctx, functionName):
    try:
        client = ctx.client('lambda')
        response = client.get_function(
            FunctionName=functionName
        )
        return response
    except botocore.exceptions.ClientError as e:
        if _is_resource_not_found(e): return None
        erm = _fail(e, 'get_function', functionName)
        raise Exception(erm)

# Allow lambda:CreateFunction
def createLambdaFunction(ctx, functionName, roleArn, cfg, codePath):
    zipBytes = getZipCodeBytes(codePath, functionName)
    try:
        client = ctx.client('lambda')
        response = client.create_function(
            FunctionName=functionName,
            Runtime=cfg['Runtime'],
            Role=roleArn,
            Handler=cfg['Handler'],
            Description=cfg['Description'],
            Timeout=cfg['Timeout'],
            MemorySize=cfg['MemorySize'],
            Code={
                'ZipFile': zipBytes
            }
        )
        return response
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'create_function', functionName)
        raise Exception(erm)

# Allow lambda:UpdateFunctionConfiguration
def updateLambdaFunctionConfiguration(ctx, functionName, roleArn, cfg):
    try:
        client = ctx.client('lambda')
        response = client.update_function_configuration(
            FunctionName=functionName,
            Runtime=cfg['Runtime'],
            Role=roleArn,
            Handler=cfg['Handler'],
            Description=cfg['Description'],
            Timeout=cfg['Timeout'],
            MemorySize=cfg['MemorySize']
        )
        return response
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'update_function_configuration', functionName)
        raise Exception(erm)

# Allow lambda:UpdateFunctionCode
def updateLambdaFunctionCode(ctx, functionName, codePath):
    zipBytes = getZipCodeBytes(codePath, functionName)
    try:
        client = ctx.client('lambda')
        response = client.update_function_code(
            FunctionName=functionName,
            ZipFile=zipBytes
        )
        return response
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'update_function_code', functionName)
        raise Exception(erm)

def getLambdaPolicy(ctx, functionArn):
    try:
        client = ctx.client('lambda')
        response = client.get_policy(
            FunctionName=functionArn
        )
        return response
    except botocore.exceptions.ClientError as e:
        if _is_resource_not_found(e): return None
        erm = _fail(e, 'get_policy', functionArn)
        raise Exception(erm)

def removeLambdaPolicy(ctx, functionArn, sid):
    try:
        client = ctx.client('lambda')
        client.remove_permission(
            FunctionName=functionArn,
            StatementId = sid
        )
        return True
    except botocore.exceptions.ClientError as e:
        if _is_resource_not_found(e): return False
        erm = _fail(e, 'remove_permission', functionArn)
        raise Exception(erm)

def addLambdaPolicyForEventRule(ctx, functionArn, sid, ruleArn):
    try:
        client = ctx.client('lambda')
        client.add_permission(
            FunctionName=functionArn,
            StatementId = sid,
            Action = "lambda:InvokeFunction",
            Principal = "events.amazonaws.com",
            SourceArn = ruleArn
        )
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'add_permission', functionArn)
        raise Exception(erm)


def declareLambdaPolicyForEventRule(ctx, functionArn, ruleArn):
    sid = 'EventRule'
    removeLambdaPolicy(ctx, functionArn, sid)
    addLambdaPolicyForEventRule(ctx, functionArn, sid, ruleArn)


# Allow lambda:DeleteFunction
def deleteLambdaFunction(ctx, functionName):
    try:
        client = ctx.client('lambda')
        client.delete_function(
            FunctionName=functionName
        )
        return True
    except botocore.exceptions.ClientError as e:
        _fail(e, 'delete_function', functionName)
        return False

def declareLambdaFunctionArn(ctx, functionName, roleArn, cfg, codePath):
    lambdafn = getLambdaFunction(ctx, functionName)
    if lambdafn:
        updateLambdaFunctionConfiguration(ctx, functionName, roleArn, cfg)
        updateLambdaFunctionCode(ctx, functionName, codePath)
        return lambdafn['Configuration']['FunctionArn']
    lambdafnNew = createLambdaFunction(ctx, functionName, roleArn, cfg, codePath)
    return lambdafnNew['FunctionArn']

def invokeLambdaFunction(ctx, functionName, payloadMap):
    try:
        client = ctx.client('lambda')
        response = client.invoke(
            FunctionName=functionName,
            InvocationType='RequestResponse',
            Payload=json.dumps(payloadMap).encode("utf-8")
        )
        payload = json.loads(response['Payload'].read().decode("utf-8"))
        print(payload)
        return {
            'StatusCode': response['StatusCode'],
            'Payload': payload
        }
    except botocore.exceptions.ClientError as e:
        _fail(e, 'invoke', functionName)
        return None

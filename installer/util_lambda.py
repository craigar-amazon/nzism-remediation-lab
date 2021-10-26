import json
import botocore
import boto3

from util_file import getZipCodeBytes

def _is_resource_not_found(e):
    return e.response['Error']['Code'] == 'ResourceNotFoundException'    

def _fail(e, op, functionName):
    print("Unexpected error calling lambda."+op)
    print("functionName: "+functionName)
    print(e)
    return "Unexpected error calling {} on {}".format(op, functionName)

# Allow lambda:GetFunction
def getLambdaFunction(functionName):
    try:
        lambda_client = boto3.client('lambda')
        response = lambda_client.get_function(
            FunctionName=functionName
        )
        return response
    except botocore.exceptions.ClientError as e:
        if _is_resource_not_found(e): return None
        erm = _fail(e, 'get_function', functionName)
        raise Exception(erm)

# Allow lambda:CreateFunction
def createLambdaFunction(functionName, roleArn, cfg, codePath):
    zipBytes = getZipCodeBytes(codePath, functionName)
    try:
        lambda_client = boto3.client('lambda')
        response = lambda_client.create_function(
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
def updateLambdaFunctionConfiguration(functionName, roleArn, cfg):
    try:
        lambda_client = boto3.client('lambda')
        response = lambda_client.update_function_configuration(
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
def updateLambdaFunctionCode(functionName, codePath):
    zipBytes = getZipCodeBytes(codePath, functionName)
    try:
        lambda_client = boto3.client('lambda')
        response = lambda_client.update_function_code(
            FunctionName=functionName,
            ZipFile=zipBytes
        )
        return response
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'update_function_code', functionName)
        raise Exception(erm)

def getLambdaPolicy(functionArn):
    try:
        lambda_client = boto3.client('lambda')
        response = lambda_client.get_policy(
            FunctionName=functionArn
        )
        return response
    except botocore.exceptions.ClientError as e:
        if _is_resource_not_found(e): return None
        erm = _fail(e, 'get_policy', functionArn)
        raise Exception(erm)

def removeLambdaPolicy(functionArn, sid):
    try:
        lambda_client = boto3.client('lambda')
        lambda_client.remove_permission(
            FunctionName=functionArn,
            StatementId = sid
        )
        return True
    except botocore.exceptions.ClientError as e:
        if _is_resource_not_found(e): return False
        erm = _fail(e, 'remove_permission', functionArn)
        raise Exception(erm)

def addLambdaPolicyForEventRule(functionArn, sid, ruleArn):
    try:
        lambda_client = boto3.client('lambda')
        lambda_client.add_permission(
            FunctionName=functionArn,
            StatementId = sid,
            Action = "lambda:InvokeFunction",
            Principal = "events.amazonaws.com",
            SourceArn = ruleArn
        )
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'add_permission', functionArn)
        raise Exception(erm)


def declareLambdaPolicyForEventRule(functionArn, ruleArn):
    sid = 'EventRule'
    removeLambdaPolicy(functionArn, sid)
    addLambdaPolicyForEventRule(functionArn, sid, ruleArn)


# Allow lambda:DeleteFunction
def deleteLambdaFunction(functionName):
    try:
        lambda_client = boto3.client('lambda')
        lambda_client.delete_function(
            FunctionName=functionName
        )
        return True
    except botocore.exceptions.ClientError as e:
        _fail(e, 'delete_function', functionName)
        return False

def declareLambdaFunctionArn(functionName, roleArn, cfg, codePath):
    lambdafn = getLambdaFunction(functionName)
    if lambdafn:
        updateLambdaFunctionConfiguration(functionName, roleArn, cfg)
        updateLambdaFunctionCode(functionName, codePath)
        return lambdafn['Configuration']['FunctionArn']
    lambdafnNew = createLambdaFunction(functionName, roleArn, cfg, codePath)
    if lambdafnNew: return lambdafnNew['FunctionArn']
    raise Exception("Could not create lambda '"+functionName+"'")

def invokeLambdaFunction(functionName, payloadMap):
    try:
        lambda_client = boto3.client('lambda')
        response = lambda_client.invoke(
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

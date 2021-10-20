import json
import botocore
import boto3

from util_file import getZipCodeBytes


# Allow lambda:GetFunction
def getLambdaFunction(functionName):
    try:
        lambda_client = boto3.client('lambda')
        response = lambda_client.get_function(
            FunctionName=functionName
        )
        return response
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return None
        print("Failed to lambda.get_function")
        print("functionName: "+functionName)
        print(e)
        return None


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
        print("Failed to lambda.create_function")
        print(e)
        return None

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
        print("Failed to lambda.update_function_configuration")
        print("functionName: "+functionName)
        print(e)
        return None

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
        print("Failed to lambda.update_function_code")
        print("functionName: "+functionName)
        print(e)
        return None

# Allow lambda:DeleteFunction
def deleteLambdaFunction(functionName):
    try:
        lambda_client = boto3.client('lambda')
        lambda_client.delete_function(
            FunctionName=functionName
        )
        return True
    except botocore.exceptions.ClientError as e:
        print("Failed to lambda.delete_function")
        print("functionName: "+functionName)
        print(e)
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
        print("Failed to lambda.invoke")
        print("functionName: "+functionName)
        print(e)
        return False
    

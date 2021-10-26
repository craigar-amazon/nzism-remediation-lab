import json
import botocore
import boto3

def getLambdaTrustPolicyJson():
    return {
        'Version': "2012-10-17",
        'Statement': [
            {
                'Effect': "Allow",
                'Principal': {
                    'Service': "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }

def getLambdaBasicPolicyArn():
    return "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"



def createIamRole(name, description, trustPolicyJson):
    policyDoc = json.dumps(trustPolicyJson)
    try:
        iam_client = boto3.client('iam')
        response = iam_client.create_role(
            Path='/',
            RoleName=name,
            AssumeRolePolicyDocument=policyDoc,
            Description=description,
            MaxSessionDuration=3600
        )
        r = response['Role']
        return r
    except botocore.exceptions.ClientError as e:
        print("Failed to iam.create_role")
        print(e)
        return None

def getIamRole(roleName):
    try:
        iam_client = boto3.client('iam')
        response = iam_client.get_role(
            RoleName=roleName
        )
        r = response['Role']
        return r
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchEntity':
            return None
        print("Failed to iam.get_role")
        print("roleName: "+roleName)
        print(e)
        return None

def attachRolePolicy(roleName, policyArn):
    try:
        iam_client = boto3.client('iam')
        iam_client.attach_role_policy(
            RoleName=roleName,
            PolicyArn=policyArn
        )
        return True
    except botocore.exceptions.ClientError as e:
        print("Failed to iam.attach_role_policy")
        print("roleName: "+roleName)
        print(e)
        return False

def putRolePolicy(roleName, policyName, policyJson):
    policyDoc = json.dumps(policyJson)
    try:
        iam_client = boto3.client('iam')
        iam_client.put_role_policy(
            RoleName=roleName,
            PolicyName=policyName,
            PolicyDocument=policyDoc
        )
        return True
    except botocore.exceptions.ClientError as e:
        print("Failed to iam.put_role_policy")
        print("roleName: "+roleName)
        print("policyName: "+policyName)
        print(e)
        return False

def declareIamRole(name, description, trustPolicyJson):
    role = getIamRole(name)
    if not role:
        role = createIamRole(name, description, trustPolicyJson)
    return role

def deleteIamRole(roleName):
    try:
        iam_client = boto3.client('iam')
        iam_client.delete_role(
            RoleName=roleName
        )
    except botocore.exceptions.ClientError as e:
        print("Failed to iam.delete_role")
        print("roleName: "+roleName)
        print(e)
        return None

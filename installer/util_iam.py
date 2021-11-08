import json
import botocore
import boto3

def _is_resource_not_found(e):
    erc = e.response['Error']['Code']
    return (erc == 'NoSuchEntity') or (erc == 'ResourceNotFoundException')    


def _fail(e, op, entityName, *args):
    print("Unexpected error calling iam."+op)
    print("entityName: "+entityName)
    for a in args:
        print(a)
    print(e)
    return "Unexpected error calling {} on {}".format(op, entityName)

def _canon_path(path):
    if len(path) == 0: return '/'
    cpath = path
    if path[0] != '/':
        cpath = '/' + cpath
    if path[-1] != '/':
        cpath = cpath +'/'
    return cpath

def _policy_arn_aws(path, policyName):
    return 'arn:aws:iam::aws:policy{}{}'.format(_canon_path(path), policyName)

def _policy_arn_customer(ctx, path, policyName):
    return 'arn:aws:iam::{}:policy{}{}'.format(ctx.accountId, _canon_path(path), policyName)

def get_role(ctx, roleName):
    try:
        client = ctx.client('iam')
        response = client.get_role(
            RoleName=roleName
        )
        return response['Role']
    except botocore.exceptions.ClientError as e:
        if _is_resource_not_found(e): return None
        erm = _fail(e, 'get_role', roleName)
        raise Exception(erm)

def get_policy(ctx, policyArn):
    try:
        client = ctx.client('iam')
        response = client.get_policy(
            PolicyArn=policyArn
        )
        return response['Policy']
    except botocore.exceptions.ClientError as e:
        if _is_resource_not_found(e): return None
        erm = _fail(e, 'get_policy', policyArn)
        raise Exception(erm)

def load_policy_version_json(ctx, policyArn, versionId):
    try:
        client = ctx.client('iam')
        response = client.get_policy_version(
            PolicyArn=policyArn,
            VersionId=versionId
        )
        doc = response['PolicyVersion']['Document']
        return json.dumps(doc)
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'get_policy_version', policyArn, '{}: {}'.format('versionId', versionId))
        raise Exception(erm)

def list_policy_versions(ctx, policyArn):
    try:
        client = ctx.client('iam')
        response = client.list_policy_versions(
            PolicyArn=policyArn
        )
        if response['IsTruncated']:
            erm = 'Policy version list is truncated for {}'.format(policyArn)
            raise Exception(erm)
        nonDefaultVersions = []
        defaultVersionId = None
        for version in response['Versions']:
            versionId = version['VersionId']
            if version['IsDefaultVersion']:
                defaultVersionId = versionId
            else:
                nonDefaultVersions.append(versionId)
        if not defaultVersionId:
            erm = 'No default version for {}'.format(policyArn)
            raise Exception(erm)
        return {
            'nonDefaultVersionIdsAsc': sorted(nonDefaultVersions),
            'defaultVersionId': defaultVersionId
        }
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'list_policy_versions', policyArn)
        raise Exception(erm)

def delete_policy(ctx, policyArn):
    try:
        client = ctx.client('iam')
        client.delete_policy(
            PolicyArn=policyArn
        )
        return True
    except botocore.exceptions.ClientError as e:
        if _is_resource_not_found(e): return False
        erm = _fail(e, 'delete_policy', policyArn)
        raise Exception(erm)

def delete_policy_version(ctx, policyArn, versionId):
    try:
        client = ctx.client('iam')
        client.delete_policy_version(
            PolicyArn=policyArn,
            VersionId=versionId
        )
        return True
    except botocore.exceptions.ClientError as e:
        if _is_resource_not_found(e): return False
        erm = _fail(e, 'delete_policy_version', policyArn, '{}: {}'.format('versionId', versionId))
        raise Exception(erm)

def delete_policy_versions(ctx, policyArn):
    versionMap = list_policy_versions(ctx, policyArn)
    nonDefaultVersionIdsAsc = versionMap['nonDefaultVersionIdsAsc']
    for versionId in nonDefaultVersionIdsAsc:
        delete_policy_version(ctx, policyArn, versionId)

def prune_policy_versions(ctx, policyArn, keepCount):
    versionMap = list_policy_versions(ctx, policyArn)
    nonDefaultVersionIdsAsc = versionMap['nonDefaultVersionIdsAsc']
    count = len(nonDefaultVersionIdsAsc)
    for versionId in nonDefaultVersionIdsAsc:
        if count <= keepCount:
            break
        delete_policy_version(ctx, policyArn, versionId)
        count = count - 1


def create_policy_arn(ctx, policyPath, policyName, policyDescription, policyJson):
    try:
        client = ctx.client('iam')
        response = client.create_policy(
            PolicyName = policyName,
            Path = policyPath,
            PolicyDocument = policyJson,
            Description = policyDescription
        )
        return response['Policy']['Arn']
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'create_policy', policyName, '{}: {}'.format('path', policyPath))
        raise Exception(erm)

def create_policy_version_id(ctx, policyArn, policyJson):
    try:
        client = ctx.client('iam')
        response = client.create_policy_version(
            PolicyArn = policyArn,
            PolicyDocument = policyJson,
            SetAsDefault = True
        )
        return response['PolicyVersion']['VersionId']
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'create_policy_version', policyArn)
        raise Exception(erm)


def create_role_arn(ctx, roleName, roleDescription, trustPolicyJson, rolePath, maxSessionSecs):
    try:
        client = ctx.client('iam')
        response = client.create_role(
            Path=rolePath,
            RoleName=roleName,
            AssumeRolePolicyDocument=trustPolicyJson,
            Description=roleDescription,
            MaxSessionDuration=maxSessionSecs
        )
        return response['Role']['Arn']
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'create_role', roleName)
        raise Exception(erm)

def update_role(ctx, roleName, roleDescription, maxSessionSecs):
    try:
        client = ctx.client('iam')
        client.update_role(
            RoleName=roleName,
            Description=roleDescription,
            MaxSessionDuration=maxSessionSecs
        )
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'update_role', roleName)
        raise Exception(erm)

def update_assume_role_policy(ctx, roleName, trustPolicyJson):
    try:
        client = ctx.client('iam')
        client.update_assume_role_policy(
            RoleName=roleName,
            PolicyDocument=trustPolicyJson
        )
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'update_assume_role_policy', roleName)
        raise Exception(erm)

def delete_role(ctx, roleName):
    try:
        client = ctx.client('iam')
        client.delete_role(
            RoleName=roleName
        )
        return True
    except botocore.exceptions.ClientError as e:
        if _is_resource_not_found(e): return False
        erm = _fail(e, 'delete_role', roleName)
        raise Exception(erm)


def declareAwsPolicyArn(ctx, policyName, policyPath='/service-role/'):
    policyArn = _policy_arn_aws(policyPath, policyName)
    exPolicy = get_policy(ctx, policyArn)
    if not exPolicy:
        erm = "AWS Policy {} is undefined".format(policyArn)
        raise Exception(erm)
    exPolicyArn = exPolicy['Arn']
    return exPolicyArn

def declareCustomerPolicyArn(ctx, policyName, policyDescription, policyMap, policyPath='/', keepVersionCount=3):
    policyArn = _policy_arn_customer(ctx, policyPath, policyName)
    reqdPolicyJson = json.dumps(policyMap)
    exPolicy = get_policy(ctx, policyArn)
    if not exPolicy:
        newArn = create_policy_arn(ctx, policyPath, policyName, policyDescription, reqdPolicyJson)
        return newArn
    
    exPolicyArn = exPolicy['Arn']
    exPolicyVersionId = exPolicy['DefaultVersionId']
    exPolicyJson = load_policy_version_json(ctx, exPolicyArn, exPolicyVersionId)
    if exPolicyJson == reqdPolicyJson:
        return exPolicyArn

    create_policy_version_id(ctx, exPolicyArn, reqdPolicyJson)
    prune_policy_versions(ctx, exPolicyArn, keepVersionCount)
    return exPolicyArn

def deleteCustomerPolicy(ctx, policyArn):
    delete_policy_versions(ctx, policyArn)
    delete_policy(ctx, policyArn)


def attach_role_policy(ctx, roleName, policyArn):
    return

def getRole(ctx, roleName):
    return get_role(ctx, roleName)

def declareRoleArn(ctx, roleName, roleDescription, trustPolicyMap, rolePath='/', maxSessionSecs=3600):
    reqdTrustPolicyJson = json.dumps(trustPolicyMap)
    exRole = get_role(ctx, roleName)
    if not exRole:
        rolePathCanon = _canon_path(rolePath)
        newArn = create_role_arn(ctx, roleName, roleDescription, reqdTrustPolicyJson, rolePathCanon, maxSessionSecs)
        return newArn

    exArn = exRole['Arn']
    exDescription = exRole['Description']
    exMaxSession = exRole['MaxSessionDuration']
    if (exDescription != roleDescription) or (exMaxSession != maxSessionSecs):
        update_role(ctx, roleName, roleDescription, maxSessionSecs)

    exTrustPolicyJson = json.dumps(exRole['AssumeRolePolicyDocument'])
    if exTrustPolicyJson != reqdTrustPolicyJson:
        update_assume_role_policy(ctx, roleName, reqdTrustPolicyJson)

    return exArn


def deleteRole(ctx, roleName):
    delete_role(ctx, roleName)


def trustPolicyLambda():
    return trustPolicyService("lambda.amazonaws.com")


def trustPolicyService(serviceName):
    return {
        'Version': "2012-10-17",
        'Statement': [
            {
                'Effect': "Allow",
                'Principal': {
                    'Service': serviceName
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }

def permissionsPolicy(statements):
    return {
        'Version': "2012-10-17",
        'Statement': statements
    }

def permissionsPolicySQS(queueArn):
    statement = {
        'Effect': "Allow",
        'Action': [
            "sqs:ReceiveMessage",
            "sqs:DeleteMessage",
            "sqs:GetQueueAttributes"
        ],
        'Resource': queueArn
    }
    return permissionsPolicy([statement])


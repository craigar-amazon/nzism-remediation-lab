import json
import botocore
from util_base import Context 

def _fail(e, op, desc, *args):
    print("Unexpected error calling kms."+op)
    print("cmk: "+desc)
    for a in args:
        print(a)
    print(e)
    return "Unexpected error calling {} on {}".format(op, desc)

def _is_resource_not_found(e):
    return e.response['Error']['Code'] == 'NotFoundException'

def policy_statement_default(ctx):
    sid = "Enable IAM policies"
    principalArn = "arn:aws:iam::{}:root".format(ctx.accountId)
    return {
        'Sid': sid,
        'Effect': "Allow",
        'Principal': {
            'AWS': principalArn
        },
        'Action': "kms:*",
        'Resource': "*" 
    }

def policy_map(statements):
    return {
    'Version': "2012-10-17",
    'Statement': statements
    }

def policyStatementService(serviceName):
    sid = "Producer service "+serviceName
    return {
        'Sid': sid,
        'Effect': "Allow",
        'Principal': {
            'Service': serviceName
        },
        'Action': [
            "kms:Decrypt",
            "kms:GenerateDataKey"

        ],
        'Resource': '*'
    }

def policyStatementEventbridge():
    return policyStatementService("events.amazonaws.com")

def canon_alias(aliasName):
    return "alias/"+aliasName

def create_key_arn(ctx, description, policyJson):
    try:
        client = ctx.session.client('kms')
        response = client.create_key(
            KeySpec="SYMMETRIC_DEFAULT",
            Description=description,
            Policy=policyJson
        )
        meta = response['KeyMetadata']
        return meta['Arn']
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'create_key', description)
        raise Exception(erm)

def create_alias(ctx, aliasName, cmkArn):
    try:
        client = ctx.session.client('kms')
        client.create_alias(
            AliasName=aliasName,
            TargetKeyId=cmkArn
        )
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'create_alias', aliasName)
        raise Exception(erm)

def put_key_policy(ctx, cmkArn, policyJson):
    try:
        client = ctx.session.client('kms')
        client.put_key_policy(
            KeyId=cmkArn,
            PolicyName='default',
            Policy=policyJson
        )
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'put_key_policy', cmkArn)
        raise Exception(erm)

def get_key_rotation_status(ctx, cmkArn):
    try:
        client = ctx.session.client('kms')
        response = client.get_key_rotation_status(
            KeyId=cmkArn
        )
        return response['KeyRotationEnabled']
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'get_key_rotation_status', cmkArn)
        raise Exception(erm)

def get_key_policy(ctx, cmkArn):
    try:
        client = ctx.session.client('kms')
        response = client.get_key_policy(
            KeyId=cmkArn,
            PolicyName='default'
        )
        return response['Policy']
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'get_key_policy', cmkArn)
        raise Exception(erm)


def update_key_description(ctx, cmkArn, description):
    try:
        client = ctx.session.client('kms')
        client.update_key_description(
            KeyId=cmkArn,
            Description=description
        )
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'update_key_description', cmkArn)
        raise Exception(erm)

def enable_key_rotation(ctx, cmkArn):
    try:
        client = ctx.session.client('kms')
        client.enable_key_rotation(
            KeyId=cmkArn
        )
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'enable_key_rotation', cmkArn)
        raise Exception(erm)

def schedule_key_deletion(ctx, cmkArn, pendingWindowInDays):
    try:
        client = ctx.session.client('kms')
        client.schedule_key_deletion(
            KeyId=cmkArn,
            PendingWindowInDays=pendingWindowInDays
        )
    except botocore.exceptions.ClientError as e:
        if _is_resource_not_found(e): return None
        erm = _fail(e, 'schedule_key_deletion', cmkArn)
        raise Exception(erm)

def delete_alias(ctx, canonAlias):
    try:
        client = ctx.session.client('kms')
        client.delete_alias(
            AliasName=canonAlias
        )
    except botocore.exceptions.ClientError as e:
        if _is_resource_not_found(e): return None
        erm = _fail(e, 'delete_alias', canonAlias)
        raise Exception(erm)

def getCMKMeta(ctx, keyId):
    try:
        client = ctx.session.client('kms')
        response = client.describe_key(
            KeyId=keyId
        )
        return response['KeyMetadata']
    except botocore.exceptions.ClientError as e:
        if _is_resource_not_found(e): return None
        erm = _fail(e, 'describe_key', keyId)
        raise Exception(erm)

def declareCMK(ctx, description, alias, policyStatements):
    statements = [policy_statement_default(ctx)]
    statements.extend(policyStatements)
    policyMap = policy_map(statements)
    reqdPolicyJson = json.dumps(policyMap)
    canonAlias = canon_alias(alias)
    exMeta = getCMKMeta(ctx, canonAlias)
    createReqd = False
    if exMeta:
        keyState = exMeta['KeyState']
        if keyState == 'PendingDeletion':
            createReqd = True
        elif keyState == 'Enabled':
            createReqd = False
        else:
            erm = 'KMS CMK {} in unexpected state {}'.format(alias, keyState)
            raise Exception(erm)
    else:
        createReqd = True
    if createReqd:
        newArn = create_key_arn(ctx, description, reqdPolicyJson)
        create_alias(ctx, canonAlias, newArn)
        enable_key_rotation(ctx, newArn)
        return newArn
    exArn = exMeta['Arn']
    exDescription = exMeta['Description']
    exPolicyJson = get_key_policy(ctx, exArn)
    exPolicyJsonCanon = json.dumps(json.loads(exPolicyJson))
    if exPolicyJsonCanon != reqdPolicyJson:
        put_key_policy(ctx, exArn, reqdPolicyJson)
    if exDescription != description:
        update_key_description(ctx, exArn, description)
    isRotationEnabled = get_key_rotation_status(ctx, exArn)
    if not isRotationEnabled:
        enable_key_rotation(ctx, exArn)
    return exArn


def deleteCMK(ctx, alias, pendingWindowInDays=7):
    canonAlias = canon_alias(alias)
    exMeta = getCMKMeta(ctx, canonAlias)
    if exMeta:
        exArn = exMeta['Arn']
        delete_alias(ctx, canonAlias)
        schedule_key_deletion(ctx, exArn, pendingWindowInDays)

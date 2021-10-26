import json
import botocore
import boto3

def _fail(e, op, stackSetName):
    print("Unexpected error calling cloudformation."+op)
    print("stackSetName: "+stackSetName)
    print(e)
    return "Unexpected error calling {} on {}".format(op, stackSetName)

def _is_resource_not_found(e):
    return e.response['Error']['Code'] == 'StackSetNotFoundException'

def _map_to_json(map):
    return json.dumps(map, indent=2)

def _canon_json(rawJson):
    map = json.loads(rawJson)
    return _map_to_json(map)

def _canon_array(array):
    return ','.join(sorted(array))

def is_matching_stack_set(ex, reqd):
    canonTemplateBody = _canon_json(ex['TemplateBody'])
    reqdTemplateBody = reqd['TemplateBody']
    if canonTemplateBody != reqdTemplateBody: return False
    if ex['Description'] != reqd['Description']: return False
    if ex['PermissionModel'] != reqd['PermissionModel']: return False
    if ex['AutoDeployment']['Enabled'] != reqd['AutoDeployment']['Enabled']: return False
    if ex['AutoDeployment']['RetainStacksOnAccountRemoval'] != reqd['AutoDeployment']['RetainStacksOnAccountRemoval']: return False
    if _canon_array(ex['Capabilities']) != _canon_array(reqd['Capabilities']): return False
    return True


def declareStackSetIdForOrganization(stackSetName, templateMap, stackSetDescription, orgunitids, regions):
    templateJson = _map_to_json(templateMap)
    reqd = {
        'Description': stackSetDescription,
        'TemplateBody': templateJson,
        'PermissionModel': 'SERVICE_MANAGED',
        'AutoDeployment' : {
                'Enabled': True,
                'RetainStacksOnAccountRemoval': False
            },
        'Capabilities': ['CAPABILITY_NAMED_IAM']
    }

    ex = describe_stackset_for_organization(stackSetName)
    if ex:
        if not is_matching_stack_set(ex, reqd):
            update_stackset_id_for_organization(stackSetName, reqd)
        return ex['StackSetId']
    stacksetId = create_stackset_id_for_organization(stackSetName, reqd)
    create_stack_instances_for_organization(stackSetName, orgunitids, regions)
    return stacksetId

def describe_stackset_for_organization(stackSetName):
    try:
        cfn_client = boto3.client('cloudformation')
        response = cfn_client.describe_stack_set(
            StackSetName=stackSetName,
            CallAs='DELEGATED_ADMIN'
        )
        return response['StackSet']
    except botocore.exceptions.ClientError as e:
        if _is_resource_not_found(e): return None
        erm = _fail(e, 'describe_stack_set', stackSetName)
        raise Exception(erm)


def create_stackset_id_for_organization(stackSetName, reqd):
    try:
        cfn_client = boto3.client('cloudformation')
        response = cfn_client.create_stack_set(
            StackSetName=stackSetName,
            Description=reqd['Description'],
            TemplateBody=reqd['TemplateBody'],
            PermissionModel=reqd['PermissionModel'],
            AutoDeployment={
                'Enabled': reqd['AutoDeployment']['Enabled'],
                'RetainStacksOnAccountRemoval': reqd['AutoDeployment']['RetainStacksOnAccountRemoval']
            },
            Capabilities = reqd['Capabilities'],
            CallAs='DELEGATED_ADMIN'
        )
        return response['StackSetId']
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'create_stack_set', stackSetName)
        raise Exception(erm)

def create_stack_instances_for_organization(stackSetName, orgunitids, regions):
    try:
        cfn_client = boto3.client('cloudformation')
        cfn_client.create_stack_instances(
            StackSetName=stackSetName,
            DeploymentTargets={
                'OrganizationalUnitIds': orgunitids
            },
            Regions=regions,
            CallAs='DELEGATED_ADMIN'
        )
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'create_stack_instances', stackSetName)
        raise Exception(erm)


def update_stackset_id_for_organization(stackSetName, reqd):
    try:
        cfn_client = boto3.client('cloudformation')
        cfn_client.update_stack_set(
            StackSetName=stackSetName,
            Description=reqd['Description'],
            TemplateBody=reqd['TemplateBody'],
            PermissionModel=reqd['PermissionModel'],
            AutoDeployment={
                'Enabled': reqd['AutoDeployment']['Enabled'],
                'RetainStacksOnAccountRemoval': reqd['AutoDeployment']['RetainStacksOnAccountRemoval']
            },
            Capabilities = reqd['Capabilities'],
            CallAs='DELEGATED_ADMIN'
        )
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'update_stack_set', stackSetName)
        raise Exception(erm)

def delete_stack_instances_for_organization(stackSetName, orgunitids, regions):
    try:
        cfn_client = boto3.client('cloudformation')
        cfn_client.delete_stack_instances(
            StackSetName=stackSetName,
            DeploymentTargets={
                'OrganizationalUnitIds': orgunitids
            },
            Regions=regions,
            RetainStacks = False,
            CallAs='DELEGATED_ADMIN'
        )
        return True
    except botocore.exceptions.ClientError as e:
        if _is_resource_not_found(e): return False
        erm = _fail(e, 'delete_stack_instances', stackSetName)
        raise Exception(erm)


def delete_stackset_for_organization(stackSetName):
    try:
        cfn_client = boto3.client('cloudformation')
        cfn_client.delete_stack_set(
            StackSetName=stackSetName,
            CallAs='DELEGATED_ADMIN'
        )
        return True
    except botocore.exceptions.ClientError as e:
        if _is_resource_not_found(e): return False
        erm = _fail(e, 'delete_stack_set', stackSetName)
        raise Exception(erm)


def deleteStackSetForOrganization(stackSetName, orgunitids, regions):
    delete_stack_instances_for_organization(stackSetName, orgunitids, regions)
    delete_stackset_for_organization(stackSetName)
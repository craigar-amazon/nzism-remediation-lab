import botocore
import boto3

def _is_resource_not_found(e):
    erc = e.response['Error']['Code']
    return (erc == 'NoSuchEntity') or (erc == 'ResourceNotFoundException')    


def _fail(e, op, roleName):
    print("Unexpected error calling iam."+op)
    print("roleName: "+roleName)
    print(e)
    return "Unexpected error calling {} on {}".format(op, roleName)

def getIamRole(roleName):
    try:
        iam_client = boto3.client('iam')
        response = iam_client.get_role(
            RoleName=roleName
        )
        r = response['Role']
        return r
    except botocore.exceptions.ClientError as e:
        if _is_resource_not_found(e): return None
        erm = _fail(e, 'get_role', roleName)
        raise Exception(erm)

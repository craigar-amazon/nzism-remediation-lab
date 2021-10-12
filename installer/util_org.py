import sys
import botocore
import boto3

def describeOrganization():
    try:
        org_client = boto3.client('organizations')
        response = org_client.describe_organization()
        r = response['Organization']
        return r
    except botocore.exceptions.ClientError as e:
        print("Failed to organizations.describe_organization")
        print(e)
        return None




org = describeOrganization()
if not org:
    sys.exit("Cannot continue without Organization information")
print("Organization Id: "+org['Id'])
print("Management Account: "+org['MasterAccountId'] + " " + org['MasterAccountEmail'])

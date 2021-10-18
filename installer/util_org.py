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

def listRoots():
    rootIdByName = {}
    try:
        org_client = boto3.client('organizations')
        paginator_roots = org_client.get_paginator("list_roots")
        page_iterator_roots = paginator_roots.paginate()
        for page_roots in page_iterator_roots:
            roots = page_roots["Roots"]
            for root in roots:
                rootName = root['Name']
                rootId = root['Id']
                rootIdByName[rootName] = rootId
        return rootIdByName
    except botocore.exceptions.ClientError as e:
        print("Failed to organizations.list_roots")
        print(e)
        return None

def listOrganizationalUnits(parentId):
    ouIdByName = {}
    try:
        org_client = boto3.client('organizations')
        paginator_ous = org_client.get_paginator("list_organizational_units_for_parent")
        page_iterator_ous = paginator_ous.paginate(ParentId=parentId)
        for page_ous in page_iterator_ous:
            ous = page_ous["OrganizationalUnits"]
            for ou in ous:
                ouName = ou['Name']
                ouId = ou['Id']
                ouIdByName[ouName] = ouId
        return ouIdByName
    except botocore.exceptions.ClientError as e:
        print("Failed to organizations.list_organizational_units_for_parent")
        print(e)
        return None

def listActiveCreatedOrganizationalAccounts(parentId):
    accountIdByName = {}
    try:
        org_client = boto3.client('organizations')
        paginator_accounts = org_client.get_paginator("list_accounts_for_parent")
        page_iterator_accounts = paginator_accounts.paginate(ParentId=parentId)
        for page_accounts in page_iterator_accounts:
            accounts = page_accounts["Accounts"]
            for account in accounts:
                accountName = account['Name']
                accountId = account['Id']
                if (account['Status'] == 'ACTIVE') and (account['JoinedMethod'] == 'CREATED'):
                    accountIdByName[accountName] = accountId
        return accountIdByName
    except botocore.exceptions.ClientError as e:
        print("Failed to organizations.list_accounts_for_parent")
        print(e)
        return None

rootName = 'Root'
securityOUName = 'Security'
auditAccountName = 'Audit'
logArchiveAccountName = 'Log Archive'
excludedOUNames = ['Legacy-Production']


org = describeOrganization()
if not org:
    raise Exception("Cannot continue without Organization information")

parentId = org['Id']
print("Organization Id: "+org['Id'])
print("Management Account: "+org['MasterAccountId'] + " " + org['MasterAccountEmail'])

rootIdByName = listRoots()
if not (rootName in rootIdByName):
    raise Exception("Cannot continue without Organization Root Id: Ensure account is delegated administrator")

rootId = rootIdByName[rootName]

parentId = rootId
excludedSet = set(excludedOUNames)
ouMap = listOrganizationalUnits(parentId)
if securityOUName in ouMap:
    securityAccountMap = listActiveCreatedOrganizationalAccounts(ouMap[securityOUName])
    if logArchiveAccountName in securityAccountMap:
        logArchiveAccountId = securityAccountMap[logArchiveAccountName]
    if auditAccountName in securityAccountMap:
        auditAccountId = securityAccountMap[auditAccountName]
for ouName in ouMap:
    if ouName == securityOUName:
        continue
    if ouName in excludedSet:
        continue
    childAccountMap = listActiveCreatedOrganizationalAccounts(ouMap[ouName])
    print(childAccountMap)
   


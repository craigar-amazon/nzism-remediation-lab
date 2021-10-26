import sys
import botocore
import boto3

def _fail(e, op, id):
    print("Unexpected error calling organizations."+op)
    if id:
        print("id: "+id)
    print(e)
    return "Unexpected error calling {}".format(op)

def describe_organization():
    try:
        org_client = boto3.client('organizations')
        response = org_client.describe_organization()
        r = response['Organization']
        return r
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'describe_organization')
        raise Exception(erm)

def map_root_ids_by_name():
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
        erm = _fail(e, 'list_roots')
        raise Exception(erm)

def map_ou_ids_by_name(parentId):
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
        erm = _fail(e, 'list_organizational_units_for_parent')
        raise Exception(erm)

def map_account_ids_by_name(parentId, activeOnly=True, createdOnly=True):
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
                if activeOnly and (account['Status'] != 'ACTIVE'):
                    continue
                if createdOnly and (account['JoinedMethod'] != 'CREATED'):
                    continue
                accountIdByName[accountName] = accountId
        return accountIdByName
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, 'list_accounts_for_parent')
        raise Exception(erm)

def map_account_names_by_id_recursive(parentId, excludedOUSet, activeOnly=True, createdOnly=True):
    accountNameById = {}
    accountIdByName = map_account_ids_by_name(parentId, activeOnly, createdOnly)
    for accountName in accountIdByName:
        accountId = accountIdByName[accountName]
        accountNameById[accountId] = accountName
    ouIdsByName = map_ou_ids_by_name(parentId)
    for ouName in ouIdsByName:
        if ouName in excludedOUSet:
            continue
        ouId = ouIdsByName[ouName]
        accountNameByIdSub = map_account_names_by_id_recursive(ouId, excludedOUSet, activeOnly, createdOnly)
        for accountIdSub in accountNameByIdSub:
            accountNameById[accountIdSub] = accountNameByIdSub[accountIdSub]
    return accountNameById



def describeLandingZone(excludedOUNames=[], securityOUName='Security', auditAccountName='Audit', logArchiveAccountName='Log Archive', rootName='Root'):
    lz = {}
    lz['ExcludedOUNames'] = excludedOUNames
    mgmt = describe_organization()
    if not mgmt:
        raise Exception("Cannot determine Organization information")
    lz['OrganizationId'] = mgmt['Id']
    lz['MasterAccountId'] = mgmt['MasterAccountId']
    lz['MasterAccountEmail'] = mgmt['MasterAccountEmail']
    rootIdsByName = map_root_ids_by_name()
    if not (rootName in rootIdsByName):
        print("Id for named Organization Root not found")
        print("rootName: "+rootName)
        raise Exception("Cannot determine Organization Root Id. Ensure account is delegated administrator")
    rootId = rootIdsByName[rootName]
    lz['RootName'] = rootName
    lz['RootId'] = rootId

    ouIdsByName = map_ou_ids_by_name(rootId)
    if not (securityOUName in ouIdsByName):
        print("Security OU for Landing Zone not found")
        print("Security OU Name: "+securityOUName)
        raise Exception("Cannot find required '"+securityOUName+"' OU (Security). Ensure landing zone has been initialised")
    securityOUId = ouIdsByName[securityOUName]
    lz['SecurityOUName'] = securityOUName
    lz['SecurityOUId'] = securityOUId

    securityAccountIdsByName = map_account_ids_by_name(securityOUId)
    if not (auditAccountName in securityAccountIdsByName):
        print("Audit Account for Landing Zone not found")
        print("Audit Account Name: "+auditAccountName)
        raise Exception("Cannot find required '"+auditAccountName+"' account (Audit). Ensure landing zone has been initialised")
    lz['AuditAccountName'] = auditAccountName
    lz['AuditAccountId'] = securityAccountIdsByName[auditAccountName]

    if not (logArchiveAccountName in securityAccountIdsByName):
        print("Log Archive Account for Landing Zone not found")
        print("Log Archive Account Name: "+logArchiveAccountName)
        raise Exception("Cannot find required '"+logArchiveAccountName+"' account (Log Archive). Ensure landing zone has been initialised")
    lz['LogArchiveAccountName'] = logArchiveAccountName
    lz['LogArchiveAccountId'] = securityAccountIdsByName[logArchiveAccountName]

    secNode = {}
    for securityAccountName in securityAccountIdsByName:
        if securityAccountName == auditAccountName:
            continue
        if securityAccountName == logArchiveAccountName:
            continue
        secAccountId = securityAccountIdsByName[securityAccountName]
        secNode[secAccountId] = securityAccountName
    lz['SecuritySharedAccountsById'] = secNode

    lzFactoryMembersByOUId = {}  
    excludedOUNameSet = set(excludedOUNames)
    for ouName in ouIdsByName:
        if ouName == securityOUName:
            continue
        if ouName in excludedOUNameSet:
            continue
        ouId = ouIdsByName[ouName]
        accountNameById = map_account_names_by_id_recursive(ouId, excludedOUNameSet, True, True)
        ouNode = {}
        ouNode['OUName'] = ouName
        ouNode['OUAccountsById'] = accountNameById
        lzFactoryMembersByOUId[ouId] = ouNode
    lz['FactoryMembersByOUId'] = lzFactoryMembersByOUId
    return lz  

import json
import botocore
import boto3

def _fail(e, op, *args):
    print("Unexpected error calling config."+op)
    for a in args:
        print(a)
    print(e)
    return "Unexpected error calling {}".format(op)


def describe_conformance_packs(session):
    fn = "describe_conformance_packs"
    try:
        cfg_client = session.client('config')
        paginator = cfg_client.get_paginator(fn)
        page_iterator = paginator.paginate()
        for page in page_iterator:
            results = page["ConformancePackDetails"]
            for result in results:
                print(result)
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, fn)
        raise Exception(erm)

def list_resource_noncompliance_by_rule(session, configRuleName):
    fn = "get_compliance_details_by_config_rule"
    complianceTypes = ['NON_COMPLIANT']
    map = {}
    try:
        cfg_client = session.client('config')
        paginator = cfg_client.get_paginator(fn)
        page_iterator = paginator.paginate(ConfigRuleName=configRuleName, ComplianceTypes=complianceTypes)
        for page in page_iterator:
            results = page["EvaluationResults"]
            for result in results:
                erq = result['EvaluationResultIdentifier']['EvaluationResultQualifier']
                resourceType = erq['ResourceType']
                resourceId = erq['ResourceId']
                if not (resourceType in map):
                    map[resourceType] = []
                map[resourceType].append(resourceId)
        return map
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, fn, '{}={}'.format("rule", configRuleName))
        raise Exception(erm)


def list_resource_noncompliance(session, cpackName):
    fn = "get_conformance_pack_compliance_details"
    filters = {
        'ComplianceType': 'NON_COMPLIANT' 
    }
    try:
        map = {}
        cfg_client = session.client('config')
        paginator = cfg_client.get_paginator(fn)
        page_iterator = paginator.paginate(ConformancePackName=cpackName, Filters=filters)
        for page in page_iterator:
            results = page["ConformancePackRuleEvaluationResults"]
            for result in results:
                erq = result['EvaluationResultIdentifier']['EvaluationResultQualifier']
                configRuleName = erq['ConfigRuleName']
                resourceType = erq['ResourceType']
                resourceId = erq['ResourceId']
                if not (configRuleName in map):
                    map[configRuleName] = {}
                crmap = map[configRuleName]
                if not (resourceType in crmap):
                    crmap[resourceType] = []
                crmap[resourceType].append(resourceId)
        return map
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, fn, '{}={}'.format("cpackName", cpackName))
        raise Exception(erm)

def list_noncompliant_rules(session):
    fn = "describe_compliance_by_config_rule"
    complianceTypes = ['NON_COMPLIANT']
    try:
        map = {}
        cfg_client = session.client('config')
        paginator = cfg_client.get_paginator(fn)
        page_iterator = paginator.paginate(ComplianceTypes=complianceTypes)
        for page in page_iterator:
            results = page["ComplianceByConfigRules"]
            for result in results:
                print(result)
        return map
    except botocore.exceptions.ClientError as e:
        erm = _fail(e, fn)
        raise Exception(erm)


homeSession = boto3.session.Session()
# describe_conformance_packs(homeSession)
m = list_noncompliant_rules(homeSession)
print(m)
# m = list_resource_noncompliance_by_rule(homeSession, 'ebs-in-backup-plan-conformance-pack-msjja9vn7')
# print(m)

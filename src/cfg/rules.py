import cfg.base as base
from cfg import RuleTable

# General format for config settings is:
# <property>.<action>.<accountName> - e.g. Deploy.baseline.networks
# Omit the <accountName> suffix to define the default for all accounts
# Omit the <action> suffix to define the default for all actions and accounts

ruleTable = RuleTable()
ruleTable.put('s3-account-level-public-access-blocks-periodic', {
    'Folder': 'ApplyS3BPA',
    'CanBaseline': True,
    'NZISM': 'CID:2022'
})

ruleTable.put('cloudwatch-log-group-encrypted', {
    'Folder': 'EncryptCWL',
    'CanBaseline': True,
    'NZISM': 'CID:3548+CID:3562+CID:4838',
    'Preview': False,
    'ExcludedResourceIds': '.*aws-controltower.*',
    'Deploy': {
        'CreateStack': False,
        'StackMaxSecs': base.stackMaxSecs
    }
})

def conformancePackName(): return "NZISM"

def stackNamePattern(configRuleName, action, accountName):
    return "NZISM-AutoDeployed-{}"

def manualRemediationTagName(configRuleName, action, accountName):
    return 'ManualRemediation'

def autoResourceTags(configRuleName, action, accountName):
    cpName = conformancePackName()
    tags = {
        'AutoDeployed': 'True',
        'AutoDeploymentReason': '{} Conformance'.format(cpName)
    }
    cpTag = ruleTable.lookup(configRuleName, cpName, None, action, accountName)
    if cpTag: tags[cpName] = cpTag
    return tags

def codeFolder(configRuleName, action, accountName):
    return ruleTable.lookup(configRuleName, 'Folder')

def isPreview(configRuleName, action, accountName):
    return bool(ruleTable.lookup(configRuleName, 'Preview', True))

def canRemediate(configRuleName, action, accountName):
    return ruleTable.lookup(configRuleName, 'CanRemediate', True)

def canBaseline(configRuleName, action, accountName):
    return ruleTable.lookup(configRuleName, 'CanBaseline', False)

def deploymentMethod(configRuleName, action, accountName):
    return ruleTable.lookup(configRuleName, 'Deploy')

def includedResourceIds(configRuleName, action, accountName):
    return ruleTable.lookup(configRuleName, 'IncludedResourceIds')

def excludedResourceIds(configRuleName, action, accountName):
    return ruleTable.lookup(configRuleName, 'ExcludedResourceIds')


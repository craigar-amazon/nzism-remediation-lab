import cfg.base as base

ruleTable = {}
ruleTable['s3-account-level-public-access-blocks-periodic'] = {
    'Folder': 'ApplyS3BPA'
}
ruleTable['cloudwatch-log-group-encrypted'] = {
    'Folder': 'EncryptCWL',
    'Preview': True,
    'Deploy': {
        'CreateStack': False,
        'StackMaxSecs': base.stackMaxSecs
    }
}

def codeFolder(configRuleName, accountName):
    rule :dict = ruleTable.get(configRuleName)
    return rule.get('Folder') if rule else None

def action(configRuleName, accountName):
    rule :dict = ruleTable.get(configRuleName)
    return rule.get('Action') if rule else None

def isPreview(configRuleName, accountName):
    rule :dict = ruleTable.get(configRuleName)
    return rule.get('Preview', True) if rule else True

def deploymentMethod(configRuleName, accountName):
    rule :dict = ruleTable.get(configRuleName)
    return rule.get('Deploy') if rule else None

def conformancePackName():
    return "NZISM"

def stackNamePattern(configRuleName, accountName):
    return "NZISM-AutoDeployed-{}"

def manualRemediationTagName(configRuleName, accountName):
    return 'ManualRemediation'

def autoResourceTags(configRuleName, accountName):
    return {
        'AutoDeployed': 'True',
        'AutoDeploymentReason': 'NZISM Conformance'
    }

def configRuleMapping(accountId):
    return {
        'lambda-function-public-access-prohibited': None,
        's3-account-level-public-access-blocks-periodic': 'ApplyS3BPA'
    }

def isPreviewRuleListInclusive(accountId):
    return True

def previewRuleList(accountId):
    return [
        'lambda-function-public-access-prohibited'
    ]

def conformancePackName():
    return "NZISM"

def stackNamePattern(configRuleName, accountId):
    return "NZISM-AutoDeployed-{}"

def manualRemediationTagName(configRuleName, accountId):
    return 'ManualRemediation'

def autoResourceTags(configRuleName, accountId):
    return {
        'AutoDeployed': 'True',
        'AutoDeploymentReason': 'NZISM Conformance'
    }

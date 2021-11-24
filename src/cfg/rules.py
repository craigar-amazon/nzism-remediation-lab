def configRuleMapping():
    return {
        'lambda-function-public-access-prohibited': None,
        's3-account-level-public-access-blocks-periodic': 'ApplyS3BPA'
    }


def previewRules():
    return [
        'lambda-function-public-access-prohibited'
    ]

def conformancePackName():
    return "NZISM"

def cloudwatch_log_group_encrypted():
    return {
        'kmsAlias': 'alias/cwl'
    }

def ruleConfig():
    return {
        'cloudwatch_log_group_encrypted': cloudwatch_log_group_encrypted()
    }
import cfg.base as base

ruleTimeoutSecs = base.stackMaxSecs + 60
sqsBatchSize = base.sqsBatchSize
dispatchTimeoutSecs = (ruleTimeoutSecs * sqsBatchSize) + 30
dispatchTimeoutCappedSecs = min(dispatchTimeoutSecs, base.lambdaMaxSecs)
sqsVisibilityTimeoutSecs = dispatchTimeoutCappedSecs + 30

def folderConfig():
    return {
        'CodeHome': './src',
        'LambdaFolder': 'lambdas',
        'RulesFolder': 'rules',
        'LibFolder': 'lib',
        'CfgFolder': 'cfg',
        'RuleMain': 'lambda_function.py'        
    }

def coreFunctionName(codeFolder):
    return "NZISM-Core-{}".format(codeFolder)

def ruleFunctionName(codeFolder):
    return "NZISM-AutoRemediation-{}".format(codeFolder)

def coreResourceName(baseName):
    return "NZISM-{}".format(baseName)

def coreResourceTags():
    return {
        'Application': 'NZISM Auto Remediation',
        'Release': '0.1'
    }

def coreFunctionCfg():
    return {
        'Runtime': 'python3.8',
        'Timeout': dispatchTimeoutCappedSecs,
        'MemorySize': 128,
        'Environment': {
            'Variables': {
                'LOGLEVEL': 'INFO'
            }
        }
    }

def coreEventBusCfg():
    return {
        'RuleTargetMaxAgeSecs': 12 * 3600
    }

def coreQueueCfg():
    return {
        'SqsVisibilityTimeoutSecs': sqsVisibilityTimeoutSecs,
        'SqsPollCfg': {
            'BatchSize': sqsBatchSize,
            'MaximumBatchingWindowInSeconds': 0
        }
    }

def coreCloudWatchNamespace(action):
    return "NZISM-{}".format(action)

def ruleResourceTags():
    return {
        'Application': 'NZISM Auto Remediation',
        'Release': '0.1'
    }

def ruleFunctionCfg(codeFolder):
    return {
        'Runtime': 'python3.8',
        'Timeout': ruleTimeoutSecs,
        'MemorySize': 128
    }

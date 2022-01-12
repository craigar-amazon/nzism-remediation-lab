import cfg.base as base

ruleTimeoutSecs = base.stackMaxSecs + 60
sqsBatchSize = base.sqsBatchSize
dispatchTimeoutSecs = (ruleTimeoutSecs * sqsBatchSize) + 30
dispatchTimeoutCappedSecs = min(dispatchTimeoutSecs, base.lambdaMaxSecs)
sqsVisibilityTimeoutSecs = dispatchTimeoutCappedSecs + 30

namespace = "NZISM"

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
    return "{}-Core-{}".format(namespace, codeFolder)

def ruleFunctionName(codeFolder):
    return "{}-AutoRemediation-{}".format(namespace, codeFolder)

def coreResourceName(baseName):
    return "{}-{}".format(namespace, baseName)

def coreQueueCMKAlias():
    return "queued_events"

def coreResourceTags():
    return {
        'Application': "{} Auto Remediation".format(namespace),
        'Release': '0.1'
    }

def dispatchFunctionCfg():
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
    return "{}-{}".format(namespace, action)

def coreCloudWatchDimensionList(action):
    return [
        'ConfigRule/Account/Region',
        'ConfigRule',
        'Account',
        'AutoResourceTag.NZISM/Account'
    ]

def ruleResourceTags():
    return {
        'Application': "{} Auto Remediation".format(namespace),
        'Release': '0.1'
    }

def ruleFunctionCfg(codeFolder):
    return {
        'Runtime': 'python3.8',
        'Timeout': ruleTimeoutSecs,
        'MemorySize': 128
    }

def environmentVariableNameRemediationRole():
    return 'REMEDIATIONROLE'

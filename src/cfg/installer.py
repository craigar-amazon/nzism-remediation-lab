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
        'Timeout': 600,
        'MemorySize': 128,
        'Environment': {
            'Variables': {
                'LOGLEVEL': 'INFO'
            }
        }
    }
    
def ruleResourceTags():
    return {
        'Application': 'NZISM Auto Remediation',
        'Release': '0.1'
    }

def ruleFunctionCfg():
    return {
        'Runtime': 'python3.8',
        'Timeout': 180,
        'MemorySize': 128
    }

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


def coreFunctionCfg():
    return {
        'Runtime': 'python3.8',
        'Handler': 'lambda_function.lambda_handler',
        'Timeout': 600,
        'MemorySize': 128
    }

def ruleFunctionCfg():
    return {
        'Runtime': 'python3.8',
        'Handler': 'lambda_function.lambda_handler',
        'Timeout': 180,
        'MemorySize': 128
    }

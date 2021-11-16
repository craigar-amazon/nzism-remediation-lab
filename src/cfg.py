def lambdaConfig():
    return {
        'Runtime': 'python3.8',
        'Handler': 'lambda_function.lambda_handler',
        'Timeout': 180,
        'MemorySize': 128
    }

def codeConfig():
    return {
        'CodeHome': './src',
        'LambdaFolder': 'lambdas',
        'RulesFolder': 'rules',
        'LibFolder': 'lib'
    }
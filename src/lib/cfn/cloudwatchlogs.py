def iamPrincipal(regionName):
    return {
        'Service': "logs.{}.amazonaws.com".format(regionName)
    }

def kmsEncryptionContextKey():
    return "kms:EncryptionContext:aws:logs:arn"

def kmsEncryptionContextValue(regionName, accountId, logName="*"):
    return "arn:aws:logs:{}:{}:{}".format(regionName, accountId, logName)

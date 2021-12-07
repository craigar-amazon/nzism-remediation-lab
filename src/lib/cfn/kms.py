import lib.cfn.iam as iam
from lib.base import Tags

# IAM Policy Actions
iamEncrypt = "kms:Encrypt*"
iamDecrypt = "kms:Decrypt*"
iamReEncrypt = "kms:ReEncrypt*"
iamGenerateDataKey = "kms:GenerateDataKey*"
iamDescribe = "kms:Describe*"

def KeyPolicy(accountId, statementList):
    principal0 = iam.iamPrincipal_Account(accountId)
    sid0 = "Enable IAM User Permissions"
    s0 = iam.ResourceAllow("kms:*", principal0, "*", sid=sid0)
    sx = list()
    sx.append(s0)
    sx.extend(statementList)
    return {
        'Version': "2012-10-17",
        'Statement': sx
    }

def KMS_Key(description, keyPolicy, tags :Tags, pendingWindowInDays=7):
    props = {
        'Description': description,
        'EnableKeyRotation': 'true',
        'KeyPolicy': keyPolicy,
        'Tags': tags.toList(),
        'PendingWindowInDays': pendingWindowInDays
    }
    return {
        'Type': "AWS::KMS::Key",
        'Properties': props
    }

def KMS_Alias(aliasBaseName, targetKeyId):
    props = {
        'AliasName': "alias/{}".format(aliasBaseName),
        'TargetKeyId': targetKeyId
    }
    return {
        'Type': "AWS::KMS::Alias",
        'Properties': props
    }

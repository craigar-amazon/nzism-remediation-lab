from lib.rule import RuleMain
from lib.rdq.svccfn import CfnClient

import lib.cfn as cfn
import lib.cfn.iam as iam
import lib.cfn.kms as kms
import lib.cfn.cloudwatchlogs as cwl

cmkAliasBaseName = 'cwlog'
stackDescription = "Creates CMK for encrypting CloudWatch Logs"
cmkDescription = "For use by CloudWatch Log Service"
cmkSid = "cwl"

def createTemplate(profile):
    _cmk = 'rCMK'
    _keyAlias = 'rKeyAlias'
    regionName = profile.regionName
    accountId = profile.accountId
    principal = cwl.iamPrincipal(regionName)
    condition = iam.ArnLike(cwl.kmsEncryptionContextKey(), cwl.kmsEncryptionContextValue(regionName, accountId, "*"))
    actions = [kms.iamEncrypt, kms.iamDecrypt, kms.iamReEncrypt, kms.iamGenerateDataKey, kms.iamDescribe]
    allowCwl = iam.ResourceAllow(actions, principal, "*", condition, cmkSid)
    keyPolicy = kms.KeyPolicy(accountId, [allowCwl])
    resources = {}
    resources[_cmk] = kms.KMS_Key(cmkDescription, keyPolicy)
    resources[_keyAlias] = kms.KMS_Alias(cmkAliasBaseName, cfn.Ref(_cmk))
    return cfn.Template(stackDescription, resources)

def lambda_handler(event, context):
    main = RuleMain()
    main.addHandler(
        configRuleName='cloudwatch-log-group-encrypted',
        resourceType= 'AWS::Logs::LogGroup',
        handlingMethod=associateCMK
    )
    return main.remediate(event)

def associateCMK(profile, logGroupName, context):
    
    cfnc = CfnClient(profile)
    # modified = s3c.declarePublicAccessBlock(accountId, True)
    # return {
    #     'modified': modified
    # }
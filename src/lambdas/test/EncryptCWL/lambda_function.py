from lib.rdq import Profile
from lib.rule import RuleMain, Task
from lib.rule.cmk import CMKResolver

import lib.cfn.iam as iam
import lib.cfn.kms as kms
import lib.cfn.cloudwatchlogs as cwl

cmkAliasBaseName = 'cwlog'
cmkDescription = "For use by CloudWatch Log Service"
cmkSid = "cwl"

def createCMKPolicyStatements(task :Task):
    regionName = task.regionName
    accountId = task.accountId
    principal = cwl.iamPrincipal(regionName)
    condition = iam.ArnLike(cwl.kmsEncryptionContextKey(), cwl.kmsEncryptionContextValue(regionName, accountId, "*"))
    actions = [kms.iamEncrypt, kms.iamDecrypt, kms.iamReEncrypt, kms.iamGenerateDataKey, kms.iamDescribe]
    allowCwl = iam.ResourceAllow(actions, principal, "*", condition, cmkSid)
    return [allowCwl]

def declareCMKARN(profile :Profile, task :Task):
    cmkResolver = CMKResolver(profile)
    policyStatements = createCMKPolicyStatements(task)
    return cmkResolver.declareARN(task, cmkAliasBaseName, cmkDescription, policyStatements)

def lambda_handler(event, context):
    main = RuleMain()
    main.addHandler(
        configRuleName='cloudwatch-log-group-encrypted',
        resourceType= 'AWS::Logs::LogGroup',
        handlingMethod=associateCMK
    )
    return main.remediate(event)

def associateCMK(profile :Profile, task :Task):
    cmkArn = declareCMKARN(profile, task)
    print(cmkArn)



    # modified = s3c.declarePublicAccessBlock(accountId, True)
    # return {
    #     'modified': modified
    # }
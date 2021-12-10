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

def declareCMKArn(profile :Profile, task :Task):
    cmkResolver = CMKResolver(profile)
    policyStatements = createCMKPolicyStatements(task)
    return cmkResolver.declareArn(task, cmkAliasBaseName, cmkDescription, policyStatements)

def lambda_handler(event, context):
    main = RuleMain()
    main.addRemediationHandler('cloudwatch-log-group-encrypted', 'AWS::Logs::LogGroup',remediate)
    main.addBaselineHandler('cloudwatch-log-group-encrypted', 'AWS::Logs::LogGroup',baseline)
    return main.action(event)

def baseline(profile :Profile, task :Task):
    cmkArn = declareCMKArn(profile, task)
    return {
        'cmkArn': cmkArn 
    }

def remediate(profile :Profile, task :Task):
    cmkArn = declareCMKArn(profile, task)
    return {
        'cmkArn': cmkArn 
    }

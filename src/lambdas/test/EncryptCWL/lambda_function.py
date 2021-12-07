import logging

from lib.rule import RuleMain, Task, RuleTimeoutError
from lib.rdq import Profile
from lib.rdq.svckms import KmsClient
from lib.rdq.svccfn import CfnClient

import lib.cfn as cfn
import lib.cfn.iam as iam
import lib.cfn.kms as kms
import lib.cfn.cloudwatchlogs as cwl

cmkAliasBaseName = 'cwlog'
cmkDescription = "For use by CloudWatch Log Service"
cmkSid = "cwl"

stackDescription = "Creates CMK for encrypting CloudWatch Logs"
stackMaxSecs = 300

def cmkStackName(task :Task):
    return task.stackNamePattern.format("CloudWatchLogs-CMK")


def createTemplate(task :Task):
    _cmk = 'rCMK'
    _keyAlias = 'rKeyAlias'
    regionName = task.regionName
    accountId = task.accountId
    principal = cwl.iamPrincipal(regionName)
    condition = iam.ArnLike(cwl.kmsEncryptionContextKey(), cwl.kmsEncryptionContextValue(regionName, accountId, "*"))
    actions = [kms.iamEncrypt, kms.iamDecrypt, kms.iamReEncrypt, kms.iamGenerateDataKey, kms.iamDescribe]
    allowCwl = iam.ResourceAllow(actions, principal, "*", condition, cmkSid)
    keyPolicy = kms.KeyPolicy(accountId, [allowCwl])
    resources = {}
    resources[_cmk] = kms.KMS_Key(cmkDescription, keyPolicy, task.autoResourceTags)
    resources[_keyAlias] = kms.KMS_Alias(cmkAliasBaseName, cfn.Ref(_cmk))
    return cfn.Template(stackDescription, resources)

def declareCMK(profile :Profile, task :Task):
    kmsc = KmsClient(profile)
    exCMK = kmsc.getCMKByAlias(cmkAliasBaseName)
    if exCMK: return exCMK
    stackName = cmkStackName(task)
    template = createTemplate(task)
    cfnc = CfnClient(profile)
    stackId = cfnc.declareStack(stackName, template, task.autoResourceTags)
    if task.isPreview: return None
    optStack = cfnc.getCompletedStack(stackName, stackMaxSecs)
    if not optStack:
        erm = "Stack {} did not complete within {} secs".format(stackName, stackMaxSecs)
        logging.warning("%s | Stack Id: %s",erm, stackId)
        raise RuleTimeoutError(erm)
    exCMK = kmsc.getCMKByAlias(cmkAliasBaseName)
    if exCMK: return exCMK
    erm = "Stack {} completed, but CMK `%s` is not yet available".format(stackName, cmkAliasBaseName)
    logging.warning("%s | Stack Id: %s",erm, stackId)
    raise RuleTimeoutError(erm)

def lambda_handler(event, context):
    main = RuleMain()
    main.addHandler(
        configRuleName='cloudwatch-log-group-encrypted',
        resourceType= 'AWS::Logs::LogGroup',
        handlingMethod=associateCMK
    )
    return main.remediate(event)

def associateCMK(profile :Profile, task :Task):
    optCmk = declareCMK(profile, task)
    print(optCmk)
    





    # modified = s3c.declarePublicAccessBlock(accountId, True)
    # return {
    #     'modified': modified
    # }
import logging

from lib.base import Tags
from lib.rule import Task, RuleTimeoutError

from lib.rdq import Profile
from lib.rdq.svckms import KmsClient
from lib.rdq.svccfn import CfnClient

import lib.cfn as cfn
import lib.cfn.iam as iam
import lib.cfn.kms as kms
import lib.cfn.cloudwatchlogs as cwl

class CMKResolver:
    def __init__(self, profile :Profile):
        self._profile = profile
        self._isPreviewing = profile.isPreviewing
        self._kmsClient = KmsClient(profile)

    def create_template(self, aliasBase, description, keyPolicy, tags):
        _cmk = 'rCMK'
        _keyAlias = 'rKeyAlias'
        resources = {}
        resources[_cmk] = kms.KMS_Key(description, keyPolicy, tags)
        resources[_keyAlias] = kms.KMS_Alias(aliasBase, cfn.Ref(_cmk))
        stackDescription = "Creates CMK - {}".format(description)
        return cfn.Template(stackDescription, resources)

    def declareArn(self, task :Task, aliasBase :str, description: str, policyStatements :list):
        exCMK = self._kmsClient.getCMKByAlias(aliasBase)
        if exCMK: return exCMK['Arn']
        tags = task.autoResourceTags
        createStack = task.deploymentMethod.get('CreateStack', False)
        if not createStack:
            return self._kmsClient.declareCMKArn(description, aliasBase, policyStatements, tags)
        stackMaxSecs = task.deploymentMethod.get('StackMaxSecs', 300)
        stackNameBase = "CMK-{}".format(aliasBase)
        stackName = task.stackNamePattern.format(stackNameBase)
        keyPolicy = kms.KeyPolicy(task.accountId, policyStatements)
        template = self.create_template(aliasBase, description, keyPolicy, tags)
        cfnc = CfnClient(self._profile)
        stackId = cfnc.declareStack(stackName, template, tags)
        if task.isPreview: return self._kmsClient.createPreviewArn()
        optStack = cfnc.getCompletedStack(stackName, stackMaxSecs)
        if not optStack:
            erm = "Stack {} did not complete within {} secs".format(stackName, stackMaxSecs)
            logging.warning("%s | Stack Id: %s",erm, stackId)
            raise RuleTimeoutError(erm)
        newCMK = self._kmsClient.getCMKByAlias(aliasBase)
        if not newCMK:
            erm = "Stack {} completed, but CMK {} is not yet available".format(stackName, aliasBase)
            logging.warning("%s | Stack Id: %s",erm, stackId)
            raise RuleTimeoutError(erm)
        return newCMK['Arn']

import lib.base.ruleresponse as response

from lib.rdq import Profile
from lib.rule import RuleMain, Task

from lib.rdq.svcs3control import S3ControlClient

def lambda_handler(event, context):
    main = RuleMain()
    main.addRemediationHandler('s3-account-level-public-access-blocks-periodic', 'AWS::::Account', remediate)
    main.addBaselineHandler('s3-account-level-public-access-blocks-periodic', 'AWS::::Account', baseline)
    return main.action(event)

def baseline(profile :Profile, task :Task):
    accountId = task.accountId
    s3c = S3ControlClient(profile)
    modified = s3c.declarePublicAccessBlock(accountId, True)
    return response.BaselineConfirmed("S3 public access block confirmed. Modified={}".format(modified))

def remediate(profile :Profile, task :Task):
    accountId = task.accountId
    s3c = S3ControlClient(profile)
    modified = s3c.declarePublicAccessBlock(accountId, True)
    if not modified: return response.RemediationValidated("S3 public access block already active")
    return response.RemediationApplied("S3 public access block applied")


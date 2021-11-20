from lib.rule import RuleMain
from lib.rdq.svcs3control import S3ControlClient

def lambda_handler(event, context):
    main = RuleMain('S3BPA')
    main.addHandler(
        configRuleName='s3-account-level-public-access-blocks-periodic',
        resourceType= 'AWS::::Account',
        handlingMethod=applyS3BlockPublicAccess
    )
    return main.remediate(event)

def applyS3BlockPublicAccess(profile, accountId, context):
    s3c = S3ControlClient(profile)
    modified = s3c.declarePublicAccessBlock(accountId, True)
    return {
        'modified': modified
    }
from lib.rdq import Profile
from lambdas.test.ApplyS3BPA.lambda_function import applyS3BPA

def test_s3bpa():
    targetAccountId = '119399605612'
    event = {
        'target': {
            'awsAccountId': targetAccountId,
            'awsRegion': 'ap-southeast-2',
            'roleName': 'aws-controltower-AdministratorExecutionRole',
            'sessionName': 'Remediate-S3BPA',
            'configRuleName': 's3-account-level-public-access-blocks-periodic',
            'resourceType': 'AWS::::Account',
            'resourceId': '119399605612'
        }
    }
    profile = Profile()
    applyS3BPA(profile, targetAccountId)

test_s3bpa()
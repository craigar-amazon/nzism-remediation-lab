from lib.rdq import Profile
from lib.rdq.svcs3control import S3ControlClient

def lambda_handler(event, context):
    (success, msg, body) = handler(event)
    if (success):
        print("Success: "+msg)
    else:
        print("Failed: "+msg)
    statusCode = 200 if success else 500
    return {
        'statusCode': statusCode,
        'message': msg,
        'body': body
    }

def handler(event):
    target = event['target']
    accountId = target['awsAccountId']
    awsRegion = target['awsRegion']
    roleName = target['roleName']
    sessionName = target['sessionName']
    configRuleName = target['configRuleName']
    fromProfile = Profile(regionName=awsRegion)
    targetProfile = fromProfile.assumeRole(accountId, roleName, awsRegion, sessionName)
    resourceId = target['resourceId']
    resourceType = target['resourceType']
    if resourceType == 'AWS::::Account' and configRuleName == 's3-account-level-public-access-blocks-periodic':
        return applyS3BPA(targetProfile, resourceId, True)
    return (False, "NotApplicable", {'reason': "Unsupported resource for rule"})

def applyS3BPA(profile, accountId, requiredState):
    s3c = S3ControlClient(profile)
    modified = s3c.declarePublicAccessBlock(accountId, requiredState)
    response = {
        'modified': modified
    }

    return (True, "Done", response)

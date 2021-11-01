import env
import fix
import query

def complianceChangeEventHandler(event):
    detail = event['detail']
    resourceType = detail['resourceType']
    newEvaluationResult = detail['newEvaluationResult']
    if not ('complianceType' in newEvaluationResult):
        return (False, "Missing New Compliance Type")

    complianceType = newEvaluationResult["complianceType"]
    if not (complianceType == 'NON_COMPLIANT'):
        return (True, "No action needed- " + complianceType)

    rawConfigRuleName = detail['configRuleName']
    pos_cr_prefix = rawConfigRuleName.find("-conformance-pack-")
    if pos_cr_prefix < 0:
        configRuleName = rawConfigRuleName
    else:
        configRuleName = rawConfigRuleName[:pos_cr_prefix]
    if resourceType == "AWS::Logs::LogGroup" and configRuleName == "cloudwatch-log-group-encrypted":
        return cwlgEncrypted(event, detail)
    if resourceType == "AWS::Logs::LogGroup" and configRuleName == "cw-loggroup-retention-period-check":
        return cwlgRetention(event, detail)

    return (True, "No remediation for "+configRuleName)


def cwlgEncrypted(event, detail):
    keyId = env.getCloudWatchLogsCMK()
    if len(keyId) == 0:
        return (False, "No CloudWatch Logs CMK Id Defined")

    cmkArn = query.validCMKARN(keyId)
    if len(cmkArn) == 0:
        return (False, "Invalid CMK Id " + keyId)

    resourceId = detail['resourceId']

    if fix.associateCMKWithCWLG(resourceId, cmkArn):
        return (True, "Encrypted " + resourceId + " with " + cmkArn)

    return (False, "Failed to associate " +cmkArn + " with " +resourceId)

def cwlgRetention(event, detail):
    retentionInDays = env.getCloudWatchLogGroupMinRetentionDays()
    resourceId = detail['resourceId']
    if fix.cwlgPutRetentionPolicy(resourceId, retentionInDays):
        return (True, "Set retention for " + resourceId + " to {} days".format(retentionInDays))
    
    return (False, "Failed set retention for " + resourceId)


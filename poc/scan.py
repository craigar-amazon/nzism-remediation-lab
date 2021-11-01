import env
import fix
import query

def scanCloudwatchLogGroups(args):
    keyId = env.getCloudWatchLogsCMK()
    if len(keyId) == 0:
        return 'No CloudWatch Logs CMK Id Defined'

    cmkArn = query.validCMKARN(keyId)
    if len(cmkArn) == 0:
        return 'Invalid CMK Id '+keyId

    minRetentionDays = env.getCloudWatchLogGroupMinRetentionDays()
    cfg = {
        'cmkArn': cmkArn,
        'minRetentionDays': minRetentionDays
    }

    fixCount = query.applyCloudWatchLogGroupList(applyCloudWatchLogGroup, cfg)

    return "Fixed {} cloudwatch log groups".format(fixCount)

def applyCloudWatchLogGroup(logGroup, cfg):
    logGroupName = logGroup['logGroupName']
    delta = False
    fixCMK = not('kmsKeyId' in logGroup)
    fixRetention = False
    if 'retentionInDays' in logGroup:
      retentionDays = int(logGroup['retentionInDays'])
      fixRetention = retentionDays < cfg['minRetentionDays']
    else:
        fixRetention = True
    if fixCMK:
        if fix.associateCMKWithCWLG(logGroupName, cfg['cmkArn']):
            delta = True
    if fixRetention:
        if fix.cwlgPutRetentionPolicy(logGroupName, cfg['minRetentionDays']):
            delta = True

    return delta

def scanS3Buckets(args):
    cfg = {
    }
    query.applyS3BucketList(applyS3BucketSSLOnlyPolicy, cfg)
    return "Fixed"

def applyS3BucketSSLOnlyPolicy(bucketName, cfg):
    print(bucketName)
    policyText = query.getBucketPolicy(bucketName)
    print(policyText)
    return True
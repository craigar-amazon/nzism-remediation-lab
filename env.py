import os

def getCloudWatchLogsCMK():
    vname = 'CWL_CMK_ID'
    if vname in os.environ:
        return os.environ[vname]
    return ''

def getCloudWatchLogGroupMinRetentionDays():
    return 545

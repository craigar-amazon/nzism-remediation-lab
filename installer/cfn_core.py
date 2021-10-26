
def ref(logicalName):
    return {
        'Ref': logicalName
    }

def arn(logicalName):
    return getAtt(logicalName, 'Arn')

def getAtt(logicalName, attributeName):
    return {
        'Fn::GetAtt': [ logicalName, attributeName ]
    }


def template(description, resourceMap):
    return {
        'AWSTemplateFormatVersion': "2010-09-09",
        'Description': description,
        'Resources': resourceMap
    }
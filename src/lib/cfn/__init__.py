def Ref(logicalName):
    return {
        'Ref': logicalName
    }

def Arn(logicalName):
    return FnGetAtt(logicalName, 'Arn')

def FnGetAtt(logicalName, attributeName):
    return {
        'Fn::GetAtt': [ logicalName, attributeName ]
    }


def Template(description, resourceMap):
    return {
        'AWSTemplateFormatVersion': "2010-09-09",
        'Description': description,
        'Resources': resourceMap
    }
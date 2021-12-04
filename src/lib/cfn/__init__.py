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

def Output(description, value, exportName=None):
    o = {}
    o['Description'] = description
    o['Value'] = value
    if exportName:
        o['Export'] = {
            'Name': exportName
        }

def Template(description, resourceMap, outputMap=None):
    t = {}
    t['AWSTemplateFormatVersion'] = "2010-09-09"
    t['Description'] = description
    t['Resources'] = resourceMap
    if outputMap:
        t['Outputs'] = outputMap
    return t

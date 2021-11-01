def propEventBridgeServicePolicy():
  return propServicePolicy("events.amazonaws.com")

def propServicePolicy(serviceName):
  return {
    'Version': "2012-10-17",
    'Statement': [
      {
        'Effect': "Allow",
        'Principal': {
          'Service': serviceName
        },
        'Action': "sts:AssumeRole"
      }
  ]
}

def propAllowPutEvent(resourceEventBus):
  return propAllowStatement(["events:PutEvents"], [resourceEventBus])

def propAllowStatement(actions, resources, condition=None):
  r = {
    'Effect': "Allow",
    'Action': actions,
    'Resource': resources
  }
  if condition:
    r['Condition'] = condition
  return r

def propPolicyDocument(statements):
  return {
    'Version': "2012-10-17",
    'Statement': statements
  }

def propPermission(policyName, policyDocumentMap):
  return {
    'PolicyName': policyName,
    'PolicyDocument': policyDocumentMap
  }

def resourceRole(roleName, roleDescription, trustPolicyMap, permissions):
  return {
    'Type': "AWS::IAM::Role",
    'Properties': {
      'RoleName': roleName,
      'Path': "/",
      'Description': roleDescription,
      'AssumeRolePolicyDocument': trustPolicyMap,
      'Policies': permissions
    }
  }



def Allow(actionList, resourceList, condition=None):
  r = {
    'Effect': "Allow",
    'Action': actionList,
    'Resource': resourceList
  }
  if condition:
    r['Condition'] = condition
  return r

def PolicyDocument(statementList):
  return {
    'Version': "2012-10-17",
    'Statement': statementList
  }

def InlinePolicy(policyName, policyDocument):
  return {
    'PolicyName': policyName,
    'PolicyDocument': policyDocument
  }

def TrustPolicy(principal):
    return {
        'Version': "2012-10-17",
        'Statement': [
            {
                'Effect': "Allow",
                'Principal': principal,
                'Action': "sts:AssumeRole"
            }
        ]
    }

def rRole(roleName, description, trustPolicy, managedPolicyArnList, inlinePolicyList):
    props =  {
      'RoleName': roleName,
      'Path': "/",
      'Description': description,
      'AssumeRolePolicyDocument': trustPolicy
    }
    if managedPolicyArnList:
        props['ManagedPolicyArns'] = managedPolicyArnList
    if inlinePolicyList:
        props['Policies'] = inlinePolicyList
    return {
        'Type': "AWS::IAM::Role",
        'Properties': props
    }

def iamPrincipal_Account(accountId):
  return {
    'AWS': "arn:aws:iam::{}:root".format(accountId)
  }

def iamPrincipal_Role(accountId, roleName):
  return {
    'AWS': "arn:aws:iam::{}:role/{}".format(accountId, roleName)
  }

def ArnLike(key, value):
  kv = {}
  kv[key] = value
  return {
    'ArnLike': kv
  }

def Allow(action, resource, condition=None, sid=None):
  r = {}
  if sid: r['Sid'] = sid
  r['Effect'] = "Allow"
  r['Action'] = action
  r['Resource'] = resource
  if condition: r['Condition'] = condition
  return r

def ResourceAllow(action, principal, resource="*", condition=None, sid=None):
  r = {}
  if sid: r['Sid'] = sid
  r['Effect'] = "Allow"
  r['Principal'] = principal
  r['Action'] = action
  r['Resource'] = resource
  if condition: r['Condition'] = condition
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

def IAM_Role(roleName, description, trustPolicy, managedPolicyArnList, inlinePolicyList):
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

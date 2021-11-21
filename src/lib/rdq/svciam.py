import botocore

from lib.rdq import RdqError
from .base import ServiceUtils

def _canon_path(path):
    if len(path) == 0: return '/'
    cpath = path
    if path[0] != '/':
        cpath = '/' + cpath
    if path[-1] != '/':
        cpath = cpath +'/'
    return cpath

def _policy_arn_aws(path, policyName):
    return 'arn:aws:iam::aws:policy{}{}'.format(_canon_path(path), policyName)

class IamClient:
    def __init__(self, profile):
        service = 'iam'
        self._profile = profile
        self._client = profile.getClient(service)
        self._utils = ServiceUtils(profile, service)

    def _policy_arn_customer(self, path, policyName):
        return 'arn:aws:iam::{}:policy{}{}'.format(self._profile.accountId, _canon_path(path), policyName)

    def get_role(self, roleName):
        op = 'get_role'
        try:
            response = self._client.get_role(
                RoleName=roleName
            )
            return response['Role']
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return None
            raise RdqError(self._utils.fail(e, op, 'RoleName', roleName))

    def get_policy(self, policyArn):
        op = 'get_policy'
        try:
            response = self._client.get_policy(
                PolicyArn=policyArn
            )
            return response['Policy']
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return None
            raise RdqError(self._utils.fail(e, op, 'PolicyArn', policyArn))

    def load_policy_version_json(self, policyArn, versionId):
        op = 'get_policy_version'
        try:
            response = self._client.get_policy_version(
                PolicyArn=policyArn,
                VersionId=versionId
            )
            doc = response['PolicyVersion']['Document']
            return self._utils.to_json(doc)
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'PolicyArn', policyArn, 'VersionId', versionId))

    def list_policy_versions(self, policyArn):
        op = 'list_policy_versions'
        try:
            response = self._client.list_policy_versions(
                PolicyArn=policyArn
            )
            if response['IsTruncated']:
                erm = 'Policy version list is truncated for {}'.format(policyArn)
                raise RdqError(erm)
            nonDefaultVersions = []
            defaultVersionId = None
            for version in response['Versions']:
                versionId = version['VersionId']
                if version['IsDefaultVersion']:
                    defaultVersionId = versionId
                else:
                    nonDefaultVersions.append(versionId)
            if not defaultVersionId:
                erm = 'No default version for {}'.format(policyArn)
                raise RdqError(erm)
            return {
                'nonDefaultVersionIdsAsc': sorted(nonDefaultVersions),
                'defaultVersionId': defaultVersionId
            }
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'PolicyArn', policyArn))

    def delete_policy(self, policyArn):
        op = 'delete_policy'
        try:
            self._client.delete_policy(
                PolicyArn=policyArn
            )
            return True
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return False
            raise RdqError(self._utils.fail(e, op, 'PolicyArn', policyArn))

    def delete_policy_version(self, policyArn, versionId):
        op = 'delete_policy_version'
        try:
            self._client.delete_policy_version(
                PolicyArn=policyArn,
                VersionId=versionId
            )
            return True
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return False
            raise RdqError(self._utils.fail(e, op, 'PolicyArn', policyArn, 'VersionId', versionId))

    def create_policy_arn(self, policyPath, policyName, policyDescription, policyJson):
        op = 'create_policy'
        try:
            response = self._client.create_policy(
                PolicyName = policyName,
                Path = policyPath,
                PolicyDocument = policyJson,
                Description = policyDescription
            )
            return response['Policy']['Arn']
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'PolicyName', policyName, 'PolicyPath', policyPath))

    def create_policy_version_id(self, policyArn, policyJson):
        op = 'create_policy_version'
        try:
            response = self._client.create_policy_version(
                PolicyArn = policyArn,
                PolicyDocument = policyJson,
                SetAsDefault = True
            )
            return response['PolicyVersion']['VersionId']
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'PolicyArn', policyArn))

    def load_attached_role_policy_arnset(self, roleName):
        op = 'list_attached_role_policies'
        try:
            response = self._client.list_attached_role_policies(
                RoleName=roleName
            )
            if response['IsTruncated']:
                erm = 'Attached policy list is truncated for role {}'.format(roleName)
                raise RdqError(erm)
            policyAttachments = response['AttachedPolicies']
            arnset = set()
            for policyAttach in policyAttachments:
                arnset.add(policyAttach['PolicyArn'])
            return arnset
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return set()
            raise RdqError(self._utils.fail(e, op, 'RoleName', roleName))

    def load_inline_role_policy_nameset(self, roleName):
        op = 'list_role_policies'
        try:
            response = self._client.list_role_policies(
                RoleName=roleName
            )
            if response['IsTruncated']:
                erm = 'Inline policy list is truncated for role {}'.format(roleName)
                raise RdqError(erm)
            policyNames = response['PolicyNames']
            nameset = set()
            for policyName in policyNames:
                nameset.add(policyName)
            return nameset
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return set()
            raise RdqError(self._utils.fail(e, op, 'RoleName', roleName))

    def attach_role_managed_policy(self, roleName, policyArn):
        op = 'attach_role_policy'
        try:
            self._client.attach_role_policy(
                RoleName=roleName,
                PolicyArn=policyArn
            )
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'RoleName', roleName, 'PolicyArn', policyArn))

    def detach_role_managed_policy(self, roleName, policyArn):
        op = 'detach_role_policy'
        try:
            self._client.detach_role_policy(
                RoleName=roleName,
                PolicyArn=policyArn
            )
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'RoleName', roleName, 'PolicyArn', policyArn))

    def get_role_inline_policy_json(self, roleName, policyName):
        op = 'get_role_policy'
        try:
            response = self._client.get_role_policy(
                RoleName=roleName,
                PolicyName=policyName
            )
            src = response['PolicyDocument']
            return self._utils.to_json(src)
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'RoleName', roleName, 'PolicyName', policyName))

    def put_role_inline_policy(self, roleName, policyName, policyJson):
        op = 'put_role_policy'
        try:
            self._client.put_role_policy(
                RoleName=roleName,
                PolicyName=policyName,
                PolicyDocument=policyJson
            )
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'RoleName', roleName, 'PolicyName', policyName))

    def delete_role_inline_policy(self, roleName, policyName):
        op = 'put_role_policy'
        try:
            self._client.delete_role_policy(
                RoleName=roleName,
                PolicyName=policyName
            )
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'RoleName', roleName, 'PolicyName', policyName))

    def create_role_arn(self, roleName, roleDescription, trustPolicyJson, rolePath, maxSessionSecs):
        op = 'create_role'
        try:
            response = self._client.create_role(
                Path=rolePath,
                RoleName=roleName,
                AssumeRolePolicyDocument=trustPolicyJson,
                Description=roleDescription,
                MaxSessionDuration=maxSessionSecs
            )
            return response['Role']['Arn']
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'RoleName', roleName))

    def update_role(self, roleName, roleDescription, maxSessionSecs):
        op = 'update_role'
        try:
            self._client.update_role(
                RoleName=roleName,
                Description=roleDescription,
                MaxSessionDuration=maxSessionSecs
            )
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'RoleName', roleName))

    def update_assume_role_policy(self, roleName, trustPolicyJson):
        op = 'update_role'
        try:
            self._client.update_assume_role_policy(
                RoleName=roleName,
                PolicyDocument=trustPolicyJson
            )
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op, 'RoleName', roleName))

    def delete_role(self, roleName):
        op = 'delete_role'
        try:
            self._client.delete_role(
                RoleName=roleName
            )
            return True
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return False
            raise RdqError(self._utils.fail(e, op, 'RoleName', roleName))

    def delete_policy_versions(self, policyArn):
        versionMap = self.list_policy_versions(policyArn)
        nonDefaultVersionIdsAsc = versionMap['nonDefaultVersionIdsAsc']
        for versionId in nonDefaultVersionIdsAsc:
            self.delete_policy_version(policyArn, versionId)

    def prune_policy_versions(self, policyArn, keepCount):
        versionMap = self.list_policy_versions(policyArn)
        nonDefaultVersionIdsAsc = versionMap['nonDefaultVersionIdsAsc']
        count = len(nonDefaultVersionIdsAsc)
        for versionId in nonDefaultVersionIdsAsc:
            if count <= keepCount:
                break
            self.delete_policy_version(policyArn, versionId)
            count = count - 1
    
    def getAwsPolicy(self, policyName, policyPath='/service-role/'):
        policyArn = _policy_arn_aws(policyPath, policyName)
        return self.get_policy(policyArn)

    def getCustomerPolicy(self, policyName, policyPath='/'):
        policyArn = self._policy_arn_customer(policyPath, policyName)
        return self.get_policy(policyArn)

    def declareAwsPolicyArn(self, policyName, policyPath='/service-role/'):
        policyArn = _policy_arn_aws(policyPath, policyName)
        exPolicy = self.get_policy(policyArn)
        if not exPolicy:
            erm = "AWS Policy {} is undefined".format(policyArn)
            raise RdqError(erm)
        exPolicyArn = exPolicy['Arn']
        return exPolicyArn

    def declareCustomerPolicyArn(self, policyName, policyDescription, policyMap, policyPath='/', keepVersionCount=3):
        policyArn = self._policy_arn_customer(policyPath, policyName)
        reqdPolicyJson = self._utils.to_json(policyMap)
        exPolicy = self.get_policy(policyArn)
        if not exPolicy:
            newArn = self.create_policy_arn(policyPath, policyName, policyDescription, reqdPolicyJson)
            return newArn
        
        exPolicyArn = exPolicy['Arn']
        exPolicyVersionId = exPolicy['DefaultVersionId']
        exPolicyJson = self.load_policy_version_json(exPolicyArn, exPolicyVersionId)
        if exPolicyJson == reqdPolicyJson:
            return exPolicyArn

        self.create_policy_version_id(exPolicyArn, reqdPolicyJson)
        self.prune_policy_versions(exPolicyArn, keepVersionCount)
        return exPolicyArn

    def deleteCustomerPolicy(self, policyArn):
        self.delete_policy_versions(policyArn)
        self.delete_policy(policyArn)

    def getRole(self, roleName):
        return self.get_role(roleName)


    def declareRoleArn(self, roleName, roleDescription, trustPolicyMap, rolePath='/', maxSessionSecs=3600):
        reqdTrustPolicyJson = self._utils.to_json(trustPolicyMap)
        exRole = self.get_role(roleName)
        if not exRole:
            rolePathCanon = _canon_path(rolePath)
            newArn = self.create_role_arn(roleName, roleDescription, reqdTrustPolicyJson, rolePathCanon, maxSessionSecs)
            return newArn

        exArn = exRole['Arn']
        exDescription = exRole['Description']
        exMaxSession = exRole['MaxSessionDuration']
        if (exDescription != roleDescription) or (exMaxSession != maxSessionSecs):
            self.update_role(roleName, roleDescription, maxSessionSecs)

        exTrustPolicyJson = self._utils.to_json(exRole['AssumeRolePolicyDocument'])
        if exTrustPolicyJson != reqdTrustPolicyJson:
            self.update_assume_role_policy(roleName, reqdTrustPolicyJson)

        return exArn


    def declareManagedPoliciesForRole(self, roleName, policyArns):
        reqdArnSet = set(policyArns)
        exArnSet = self.load_attached_role_policy_arnset(roleName)
        for reqdArn in reqdArnSet:
            if not (reqdArn in exArnSet):
                self.attach_role_managed_policy(roleName, reqdArn)
        for exArn in exArnSet:
            if not (exArn in reqdArnSet):
                self.detach_role_managed_policy(roleName, exArn)


    def declareInlinePoliciesForRole(self, roleName, inlinePolicyMap):
        exNameSet = self.load_inline_role_policy_nameset(roleName)
        for reqdName in inlinePolicyMap:
            reqdMap = inlinePolicyMap[reqdName]
            reqdJson = self._utils.to_json(reqdMap)
            putPolicy = True 
            if reqdName in exNameSet:
                exJson = self.get_role_inline_policy_json(roleName, reqdName)
                putPolicy = exJson != reqdJson
            if putPolicy:
                self.put_role_inline_policy(roleName, reqdName, reqdJson)
        for exName in exNameSet:
            if not (exName in inlinePolicyMap):
                self.delete_role_inline_policy(roleName, exName)

    def declarePoliciesForRole(self, roleName, managedPolicyArns, inlinePolicyMap):
        self.declareManagedPoliciesForRole(roleName, managedPolicyArns)
        self.declareInlinePoliciesForRole(roleName, inlinePolicyMap)

    def deleteRole(self, roleName):
        self.declareManagedPoliciesForRole(roleName, [])
        self.declareInlinePoliciesForRole(roleName, {})
        self.delete_role(roleName)

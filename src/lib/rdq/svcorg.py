import json
from typing import Dict, List
import botocore
from lib.rdq import RdqError
from lib.rdq.base import ServiceUtils

class AccountDescriptor:
    def __init__(self, props):
        self._props = props

    @property
    def accountId(self):
        return self._props['Id']

    @property
    def arn(self):
        return self._props['Arn']

    @property
    def accountName(self):
        return self._props['Name']

    @property
    def accountEmail(self):
        return self._props['Email']

    @property
    def status(self):
        return self._props['Status']

    @property
    def isActive(self):
        return self._props['Status'] == 'ACTIVE'

    def toDict(self) -> dict:
        return self._props

    def __str__(self):
        return json.dumps(self._props)


class OrganizationDescriptor:
    def __init__(self, props):
        self._props = props

    @property
    def id(self):
        return self._props['Id']

    @property
    def arn(self):
        return self._props['Arn']

    @property
    def masterAccountId(self):
        return self._props['MasterAccountId']

    @property
    def masterAccountEmail(self):
        return self._props['MasterAccountEmail']

    def toDict(self) -> dict:
        return self._props

    def __str__(self):
        return json.dumps(self._props)

class OrganizationUnit:
    def __init__(self, props):
        self._props = props

    @property
    def id(self):
        return self._props['Id']

    @property
    def arn(self):
        return self._props['Arn']

    @property
    def name(self):
        return self._props['Name']

    def toDict(self) -> dict:
        return self._props

    def __str__(self):
        return json.dumps(self._props)

class OrganizationUnitTree:
    def __init__(self, parentOU: OrganizationUnit):
        self._parentOU = parentOU
        self._idMap: Dict[str, OrganizationUnitTree] = {}

    @property
    def id(self): return self._parentOU.id

    def putChildTree(self, childTree):
        childId = childTree.id
        self._idMap[childId] = childTree

    def findOUById(self, id: str) -> OrganizationUnit:
        if self._parentOU.id == id: return self._parentOU
        for childTree in self._idMap.values():
            matchOU = childTree.findOUById(id)
            if matchOU: return matchOU
        return None

    def findOUByPath(self, targetPath: str, head=None) -> OrganizationUnit:
        prefix = "" if head is None else head + "/"
        actualPath = prefix + self._parentOU.name
        if actualPath == targetPath: return self._parentOU
        for childTree in self._idMap.values():
            matchOU = childTree.findOUByPath(targetPath, actualPath)
            if matchOU: return matchOU
        return None

    def matchOUByName(self, name: str) -> List[OrganizationUnit]:
        result = []
        if self._parentOU.name == name:
            result.append(self._parentOU)
        for childTree in self._idMap.values():
            result.extend(childTree.matchOUByName(name))
        return result

    def toDict(self):
        childOUs = []
        for childTree in self._idMap.values:
            childOUs.append(childTree.toDict())
        return {'parentOU': self._parentOU, 'childOUs': childOUs}

    def _fmt(self, level, indentChar, nodeMark, idSet: set, caption):
        buff = []
        indent = "" if level < 2 else ''.ljust((level - 1) * len(nodeMark), indentChar)
        prefix = "" if level < 1 else nodeMark
        ouName = self._parentOU.name
        ouId = self._parentOU.id
        highlight = caption if (ouId in idSet) else ""
        line = "{}{}{} ({}){}".format(indent, prefix, ouName, ouId, highlight)
        buff.append(line)
        for childTree in self._idMap.values():
            buff.extend(childTree._fmt((level + 1), indentChar, nodeMark, idSet, caption))
        return buff

    def pretty(self, indentChar=' ', nodeMark="+---", highlightIds=[], caption=""):
        idSet = set(highlightIds)
        buff = self._fmt(0, indentChar, nodeMark, idSet, caption)
        return '\n'.join(buff)


class OrganizationClient:
    def __init__(self, profile):
        service = 'organizations'
        self._profile = profile
        self._client = profile.getClient(service)
        self._utils = ServiceUtils(profile, service)

    def diagnosticDelegated(self, op):
        accountId = self._profile.accountId
        msg = "Ensure account is delegated administrator for Organization"
        self._utils.warning(op, "Account", accountId, msg)


    def describe_organization(self):
        op = 'describe_organization'
        try:
            response = self._client.describe_organization()
            return response['Organization']
        except botocore.exceptions.ClientError as e:
            self.diagnosticDelegated(op)
            raise RdqError(self._utils.fail(e, op))

    def describe_account(self, accountId):
        op = 'describe_account'
        try:
            response = self._client.describe_account(
                AccountId = accountId
            )
            return response['Account']
        except botocore.exceptions.ClientError as e:
            self.diagnosticDelegated(op)
            raise RdqError(self._utils.fail(e, op))

    def get_root_ou(self) -> OrganizationUnit:
        op = "list_roots"
        try:
            paginator = self._client.get_paginator(op)
            page_iterator = paginator.paginate()
            results = []
            for page in page_iterator:
                items = page["Roots"]
                for item in items:
                    results.append(OrganizationUnit(item))
            resultCount = len(results)
            if resultCount == 1: return results[0]
            raise RdqError(self._utils.integrity("Unexpected result count", "ResultCount", resultCount))
        except botocore.exceptions.ClientError as e:
            raise RdqError(self._utils.fail(e, op))

    def list_ous_for_parent(self, parentId) -> List[OrganizationUnit]:
        op = "list_organizational_units_for_parent"
        try:
            paginator = self._client.get_paginator(op)
            page_iterator = paginator.paginate(ParentId=parentId)
            ouList = []
            for page in page_iterator:
                items = page["OrganizationalUnits"]
                for item in items:
                    ouList.append(OrganizationUnit(item))
            return ouList
        except botocore.exceptions.ClientError as e:
            if self._utils.is_resource_not_found(e): return []
            raise RdqError(self._utils.fail(e, op, 'ParentId', parentId))

    def make_ou_tree(self, parentOU: OrganizationUnit, depth, tracker):
        tree = OrganizationUnitTree(parentOU)
        if tracker:
            tracker(depth, parentOU.name)
        childOUList = self.list_ous_for_parent(parentOU.id)
        for childOU in childOUList:
            childTree = self.make_ou_tree(childOU, (depth+1), tracker)
            tree.putChildTree(childTree)
        return tree

    def getOrganizationUnitTree(self, tracker=None) -> OrganizationUnitTree:
        rootOU = self.get_root_ou()
        tree = self.make_ou_tree(rootOU, 0, tracker)
        return tree

    def getOrganizationDescriptor(self) -> OrganizationDescriptor:
        return OrganizationDescriptor(self.describe_organization())

    def getAccountDescriptor(self, accountId) -> AccountDescriptor:
        return AccountDescriptor(self.describe_account(accountId))

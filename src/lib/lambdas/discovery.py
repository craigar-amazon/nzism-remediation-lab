import logging

from lib.base import selectConfig
from lib.rdq import Profile
from lib.rdq.svciam import IamClient
from lib.rdq.svcorg import OrganizationClient, AccountDescriptor, OrganizationDescriptor

import cfg.roles as cfgroles

def isLandingZoneDiscoveryEnabled():
    lzsearch = cfgroles.landingZoneSearch()
    if not lzsearch: return False
    return len(lzsearch) > 1

class LandingZoneDiscovery:
    def __init__(self, profile :Profile):
        self._profile = profile
        self._iamClient = IamClient(profile)
        self._orgClient = OrganizationClient(profile)

    def getAccountDescriptor(self, accountId) -> AccountDescriptor:
        return self._orgClient.getAccountDescriptor(accountId) 

    def getOrganizationDescriptor(self) -> OrganizationDescriptor:
        return self._orgClient.getOrganizationDescriptor()

    def discoverLandingZone(self):
        lzsearch = cfgroles.landingZoneSearch()
        if not lzsearch:
            logging.info("No landing zone configured. Will assume single account.")
            return None

        searchLength = len(lzsearch)
        lzroles = cfgroles.landingZoneRoles()
        lz = lzsearch[0]
        lzcfg = selectConfig(lzroles, "landingZoneRoles", lz)
        auditRoleName = selectConfig(lzcfg, lz, 'Audit')
        remediationRoleName = selectConfig(lzcfg, lz, 'Remediation')
        auditRoleArn = self._profile.getRoleArn(auditRoleName)
        logging.info("Preferred audit role - %s", auditRoleArn)
        if searchLength > 1:
            for lz in lzsearch:
                lzcfg = selectConfig(lzroles, "landingZoneRoles", lz)
                auditRoleName = selectConfig(lzcfg, lz, 'Audit')
                remediationRoleName = selectConfig(lzcfg, lz, 'Remediation')
                exAuditRole = self._iamClient.getRole(auditRoleName)
                if exAuditRole:
                    auditRoleArn = exAuditRole['Arn']
                    logging.info("Discovered audit role- %s", auditRoleArn)
                    break
        return {
            'LandingZone': lz,
            'AuditRoleName': auditRoleName,
            'AuditRoleArn': auditRoleArn,
            'RemediationRoleName': remediationRoleName
        }

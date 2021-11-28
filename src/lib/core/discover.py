import logging

from lib.base import selectConfig
from lib.rdq.svciam import IamClient

import cfg.roles as cfgroles

def isLandingZoneDiscoveryEnabled():
    lzsearch = cfgroles.landingZoneSearch()
    if not lzsearch: return False
    return len(lzsearch) > 1

def discoverLandingZone(profile):
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
    auditRoleArn = profile.getRoleArn(remediationRoleName)
    logging.info("Preferred audit role - %s", auditRoleArn)
    if searchLength > 1:
        iamc = IamClient(profile)
        for lz in lzsearch:
            lzcfg = selectConfig(lzroles, "landingZoneRoles", lz)
            auditRoleName = selectConfig(lzcfg, lz, 'Audit')
            remediationRoleName = selectConfig(lzcfg, lz, 'Remediation')
            exAuditRole = iamc.getRole(auditRoleName)
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

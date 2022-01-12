import logging

from lib.base import selectConfig, ConfigError
from lib.rdq import Profile
from lib.rdq.svciam import IamClient, RoleDescriptor

import cfg.roles as cfgroles

class LandingZoneDescriptor:
    def __init__(self, props):
        self._props = props

    @property
    def landingZoneType(self) -> str: return self._props.get('LandingZone')

    @property
    def auditRoleName(self) -> str: return self._props.get('AuditRoleName')

    @property
    def auditRoleArn(self) -> str: return self._props.get('AuditRoleArn')

    @property
    def remediationRoleName(self) -> str: return self._props.get('RemediationRoleName')

    def toDict(self): return self._props

class LandingZoneDiscovery:
    def __init__(self, profile :Profile):
        self._profile = profile
        self._iamClient = IamClient(profile)

    def getLandingZoneDescriptor(self) -> LandingZoneDescriptor:
        lzsearchIn = cfgroles.landingZoneSearch()
        lzsearch = list() if lzsearchIn is None else list(lzsearchIn)
        searchLength = len(lzsearch)
        if searchLength == 0:
            logging.info("No landing zone configured. Will assume stand-alone account.")
            return None

        lzroles = cfgroles.landingZoneRoles()
        for lzType in lzsearch:
            lzCfg = selectConfig(lzroles, "landingZoneRoles", lzType)
            auditRoleName = selectConfig(lzCfg, lzType, 'Audit')
            remediationRoleName = selectConfig(lzCfg, lzType, 'Remediation')
            optAuditRoleDescriptor :RoleDescriptor = self._iamClient.getRoleDescriptor(auditRoleName)
            if not optAuditRoleDescriptor: continue
            props = {
                'LandingZone': lzType,
                'AuditRoleName': auditRoleName,
                'AuditRoleArn': optAuditRoleDescriptor.arn,
                'RemediationRoleName': remediationRoleName
            }
            return LandingZoneDescriptor(props)
        
        searchPath = ", ".join(lzsearch)
        syn = "Failed to verify landing zone roles on search path: {}".format(searchPath)
        raise ConfigError(syn)

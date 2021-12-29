import logging

from lib.base import selectConfig, ConfigError
from lib.rdq import Profile
from lib.rdq.svciam import IamClient, RoleDescriptor
from lib.rdq.svcorg import OrganizationClient, AccountDescriptor, OrganizationDescriptor

import cfg.roles as cfgroles

class LandingZoneDescriptor:
    def __init__(self, props :dict=None):
        isStandalone = True
        if props:
            self._props = props
            isStandalone = False
        else:
            self._props = {}
        self._props['IsStandalone'] = isStandalone

    @property
    def isStandalone(self) -> bool: return self._props.get('IsStandalone')

    @property
    def landingZoneType(self) -> str: return self._props.get('LandingZone')

    @property
    def auditRoleName(self) -> str: return self._props.get('AuditRoleName')

    @property
    def auditRoleArn(self) -> str: return self._props.get('AuditRoleArn')

    @property
    def remediationRoleName(self) -> str: return self._props.get('RemediationRoleName')

    @property
    def isVerified(self) -> bool: return self._props.get('IsVerified')

    def toDict(self): return self._props

class LandingZoneDiscovery:
    def __init__(self, profile :Profile, requireRoleVerification=False):
        self._profile = profile
        self._iamClient = IamClient(profile)
        self._orgClient = OrganizationClient(profile)
        self._requireRoleVerification = requireRoleVerification

    def get_role_descriptor(self, roleName) -> RoleDescriptor:
        return self._iamClient.getRoleDescriptor(roleName)

    def landingzone_descriptor(self, lzType, verify) -> LandingZoneDescriptor:
        lzroles = cfgroles.landingZoneRoles()
        lzCfg = selectConfig(lzroles, "landingZoneRoles", lzType)
        auditRoleName = selectConfig(lzCfg, lzType, 'Audit')
        remediationRoleName = selectConfig(lzCfg, lzType, 'Remediation')
        auditRoleArn = self._profile.getRoleArn(auditRoleName)
        isVerified = False
        if verify:
            optAuditRoleDescriptor = self.get_role_descriptor(auditRoleName)
            if optAuditRoleDescriptor:
                auditRoleArn = optAuditRoleDescriptor.arn
                isVerified = True
        props = {
            'LandingZone': lzType,
            'AuditRoleName': auditRoleName,
            'AuditRoleArn': auditRoleArn,
            'RemediationRoleName': remediationRoleName,
            'IsVerified': isVerified
        }
        return LandingZoneDescriptor(props)
 
    def getAccountDescriptor(self, accountId) -> AccountDescriptor:
        return self._orgClient.getAccountDescriptor(accountId) 

    def getOrganizationDescriptor(self) -> OrganizationDescriptor:
        return self._orgClient.getOrganizationDescriptor()

    def getLandingZoneDescriptor(self) -> LandingZoneDescriptor:
        lzsearchIn = cfgroles.landingZoneSearch()
        lzsearch = list() if lzsearchIn is None else list(lzsearchIn)
        searchLength = len(lzsearch)
        if searchLength == 0:
            logging.info("No landing zone configured. Will assume stand-alone account.")
            return LandingZoneDescriptor()

        preferredLzType = lzsearch[0]
        preferredDescriptor = self.landingzone_descriptor(preferredLzType, verify=False)
        verifyRequired = (searchLength > 1) or self._requireRoleVerification
        if not verifyRequired: return preferredDescriptor
        for lzType in lzsearch:
            descriptor = self.landingzone_descriptor(lzType, verify=True)
            if descriptor.isVerified: return descriptor
        
        searchPath = ", ".join(lzsearch)
        syn = "Failed to verify landing zone roles on search path: {}".format(searchPath)
        raise ConfigError(syn)

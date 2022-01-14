def landingZoneSearch():
    return ['ControlTower', 'AutomatedLandingZone']

def landingZoneRoles():
    return {
        'ControlTower': {
            'Audit': 'aws-controltower-AuditAdministratorRole',
            'Remediation': 'aws-controltower-AdministratorExecutionRole'
        },
        'AutomatedLandingZone': {
            'Audit': 'AWSLandingZoneSecurityAdministratorRole',
            'Remediation': 'AWSLandingZoneAdminExecutionRole'
        }
    }

def standaloneRoles():
    return {
        'Audit': 'autoremediation-local-AuditAdministratorRole',
        'Remediation': 'autoremediation-local-AdministratorExecutionRole'
    }

def landingZoneSearch():
    return ['ControlTower', 'AutomatedLandingZone', 'LOCAL']

def landingZoneRoles():
    return {
        'ControlTower': {
            'Audit': 'aws-controltower-AuditAdministratorRole',
            'Remediation': 'aws-controltower-AdministratorExecutionRole'
        },
        'AutomatedLandingZone': {
            'Audit': 'AWSLandingZoneSecurityAdministratorRole',
            'Remedition': 'AWSLandingZoneAdminExecutionRole'
        }
    }

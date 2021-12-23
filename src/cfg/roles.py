

# Specify empty array for standalone mode
# Specifying multiple members will initiate iam:GetRole discovery
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

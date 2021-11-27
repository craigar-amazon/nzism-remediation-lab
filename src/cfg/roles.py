

# Specify empty array for single-account mode
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
            'Remedition': 'AWSLandingZoneAdminExecutionRole'
        }
    }

from lib.rdq import Profile
from lib.rdq.iam import IamClient

def handler(args):
    profile = Profile()
    iam = IamClient(profile)
    role = iam.getRole('aws-controltower-AuditAdministratorRole')
    print(role)

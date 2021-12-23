from lib.rdq import Profile
from lib.rdq.svcorg import OrganizationClient, OrganizationDescriptor

from lib.lambdas.discovery import LandingZoneDiscovery


class LandingZoneStep:
    def __init__(self, args, profile :Profile):
        landingZoneDiscovery = LandingZoneDiscovery(profile, requireRoleVerification=True)
        if args.forcelocal:
            self.localInstallEnabled = True
            print("Local installation has been specified")
        else:
            landingZoneDescriptor = landingZoneDiscovery.getLandingZoneDescriptor()
            if landingZoneDescriptor.isStandalone:
                self.localInstallEnabled = True
                print("Landing zone is not configured. Will install locally.")
            else:
                self.optLandingZoneDescriptor = landingZoneDescriptor
                print('Detected {}'.format(landingZoneDescriptor.landingZoneType))
                self.optOrgDescriptor = landingZoneDiscovery.getOrganizationDescriptor()
                print("Detected Organization ARN: {}".format(self.optOrgDescriptor.arn))

def handler(args):
    profile = Profile()
    landingZone = LandingZoneStep(args, profile)



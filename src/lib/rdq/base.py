import time
import json


class ServiceUtils:
    def __init__(self, profile, service, maxAttempts=10):
        self._profile = profile
        self._service = service
        self._maxAttempts = maxAttempts
    
    def is_resource_not_found(self, e):
        erc = e.response['Error']['Code']
        return (erc == 'NoSuchEntity') or (erc == 'ResourceNotFoundException') or (erc == 'NotFoundException')

    def is_role_propagation_delay(self, e):
        erc = e.response['Error']['Code']
        erm = e.response['Error']['Message'].lower()
        isRoleRelated = erm.find('role') >= 0
        return (erc == 'InvalidParameterValueException') and isRoleRelated

    def init_tracker(self):
        return {'waitSecs': 1, 'attempt': 1}
    
    def retry(self, tracker):
        return tracker['attempt'] < self._maxAttempts

    def backoff(self, tracker):
        waitSecs = tracker['waitSecs']
        attempt = tracker['attempt']
        time.sleep(waitSecs)
        return {'waitSecs': (waitSecs * 2), 'attempt': (attempt + 1)}

    def retry_propagation_delay(self, e, tracker):
        return self.retry(tracker) and self.is_role_propagation_delay(e)

    def to_json(self, src):
        if type(src) is str:
            map = json.loads(src)
            return json.dumps(map)
        return json.dumps(src)

    def from_json(self, src):
        if type(src) is str:
            return json.loads(src)
        return src

    def policy_map(self, statements):
        return {
            'Version': "2012-10-17",
            'Statement': statements
        }

    def fail(self, e, op, entityType, entityName, *args):
        print("Unexpected error calling {}:{}".format(self._service, op))
        print("AccountId: {}".format(self._profile.accountId))
        print("SessionName: {}".format(self._profile.sessionName))
        print("{}: {}".format(entityType, entityName))
        key = ''
        for a in args:
            if key:
                print("{}: {}".format(key, a))
                key = ''
            else:
                key = a
        if key:
            print(key)
        print(e)
        return "Unexpected error calling {} on {}".format(op, entityName)


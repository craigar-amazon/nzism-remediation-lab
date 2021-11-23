import logging
import time
import json

def _logerr(msg):
    logging.error(msg)

def _logerrargs(*args):
    key = ''
    for a in args:
        if key:
            _logerr("{}: {}".format(key, a))
            key = ''
        else:
            key = a
    if key:
        _logerr(key)

class ServiceUtils:
    def __init__(self, profile, service, maxAttempts=10):
        self._profile = profile
        self._service = service
        self._maxAttempts = maxAttempts
    
    def is_resource_not_found(self, e):
        erc = e.response['Error']['Code']
        svc = self._service
        if erc == 'ResourceNotFoundException': return True
        if erc == 'NotFoundException': return True
        if erc == 'NoSuchEntity': return True
        if svc == 'sqs':
            return erc == 'AWS.SimpleQueueService.NonExistentQueue'
        return False

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

    def sleep(self, waitSecs):
        time.sleep(waitSecs)

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

    def diagnostic(self, op, msg):
        _logerr("Diagnostic information for {}:{}".format(self._service, op))
        _logerr(msg)
        return msg

    def fail(self, e, op, entityType, entityName, *args):
        erm = "Unexpected error calling {}:{}".format(self._service, op)
        _logerr(erm)
        _logerr("AccountId: {}".format(self._profile.accountId))
        _logerr("SessionName: {}".format(self._profile.sessionName))
        if entityType and entityName:
            _logerr("{}: {}".format(entityType, entityName))
        _logerrargs(args)
        _logerr(e)
        if entityName: return "Unexpected error calling {} on {}".format(op, entityName)
        return erm

    def integrity(self, msg, *args):
        erm = "Data integrity error detected in {}".format(self._service)
        _logerr(erm)
        _logerr(msg)
        _logerr("AccountId: {}".format(self._profile.accountId))
        _logerr("SessionName: {}".format(self._profile.sessionName))
        _logerrargs(args)
        return erm


    def preview(self, op, args):
        svcop = "{}:{}".format(self._service, op)
        return self._profile.preview(svcop, args)



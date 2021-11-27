import logging
import time
import json

def _args_to_map(args):
    map = {}
    key = ''
    for a in args:
        if key:
            map[key] = a
            key = ''
        else:
            key = a
    if key:
        map[key] = True
    return map

class ServiceUtils:
    def __init__(self, profile, service, maxAttempts=10):
        self._profile = profile
        self._service = service
        self._maxAttempts = maxAttempts
    
    def service_op(self, op):
        return "{}:{}".format(self._service, op)

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

    def is_resource_conflict(self, e):
        erc = e.response['Error']['Code']
        return (erc == 'ResourceConflictException')

    def init_tracker(self, op):
        sop = self.service_op(op)
        return {'waitSecs': 1, 'attempt': 1, 'op': sop}
    
    def retry(self, tracker):
        return tracker['attempt'] < self._maxAttempts

    def backoff(self, tracker):
        waitSecs = tracker['waitSecs']
        attempt = tracker['attempt']
        logging.info("Will retry rdq operation after backoff interval | Tracker: %s", tracker)
        time.sleep(waitSecs)
        return {'waitSecs': (waitSecs * 2), 'attempt': (attempt + 1)}

    def retry_propagation_delay(self, e, tracker):
        canRetry = self.retry(tracker) and self.is_role_propagation_delay(e)
        if canRetry:
            logging.info("Retry possible after suspected role propagation error | Detail: %s", e)
        return canRetry

    def retry_resource_conflict(self, e, tracker):
        canRetry = self.retry(tracker) and self.is_resource_conflict(e)
        if canRetry:
            logging.info("Retry possible after resource conflict error | Detail: %s", e)
        return canRetry

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

    def info(self, op, argType, argValue, msg, *args):
        sop = self.service_op(op)
        argmap = _args_to_map(args)
        logging.info("%s - %s: %s | Context: %s | Service: %s", msg, argType, argValue, argmap, sop)
        return msg

    def warning(self, op, argType, argValue, msg, *args):
        sop = self.service_op(op)
        argmap = _args_to_map(args)
        ec = { argType: argValue }
        if argmap: ec['Arguments'] = argmap
        logging.warning("%s | Service: %s | Context: %s ", msg, sop, ec)
        return msg

    def fail(self, e, op, argType, argValue, *args):
        sop = self.service_op(op)
        argmap = _args_to_map(args)
        ec = { argType: argValue }
        if argmap: ec['Arguments'] = argmap
        ec['AccountId'] = self._profile.accountId,
        ec['SessionName'] = self._profile.sessionName
        logging.error("%s client error | Context: %s | Detail: %s", sop, ec, e)
        if argValue:
            erm = "{} client error for {}: `{}`".format(sop, argType, argValue)
        else:
            erm = "{} client error".format(sop)
        return erm

    def integrity(self, msg, *args):
        svc = self._service
        argmap = _args_to_map(args)
        ec = {}
        if argmap: ec['Arguments'] = argmap
        ec['AccountId'] = self._profile.accountId,
        ec['SessionName'] = self._profile.sessionName
        logging.error("%s data integrity error | Cause: %s | Context: %s", svc, msg, ec)
        erm = "{} integrity error: {}".format(svc, msg)
        return erm


    def preview(self, op, args):
        sop = self.service_op(op)
        return self._profile.preview(sop, args)



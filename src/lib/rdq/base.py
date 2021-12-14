import logging
import time
import uuid
import json


def _fmt_argval(val):
    t = type(val)
    if (t is str) or (t is int) or (t is bool): return val
    return str(val)

def _args_to_map(args):
    map = {}
    key = ''
    for a in args:
        if key:
            map[key] = _fmt_argval(a)
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

    def is_error_code(self, e, errorCode):
        erc = e.response['Error']['Code']
        return erc == errorCode

    def is_resource_not_found(self, e):
        erc = e.response['Error']['Code']
        svc = self._service
        if erc == 'ResourceNotFoundException': return True
        if erc == 'NotFoundException': return True
        if erc == 'NoSuchEntity': return True
        if svc == 'sqs':
            return erc == 'AWS.SimpleQueueService.NonExistentQueue'
        if svc == 'cloudformation':
            return (erc == 'StackSetNotFoundException') or (erc == 'OperationNotFoundException')
        return False

    def is_role_propagation_delay(self, e):
        erc = e.response['Error']['Code']
        erm = e.response['Error']['Message'].lower()
        isRoleRelated = erm.find('role') >= 0
        return (erc == 'InvalidParameterValueException') and isRoleRelated

    def is_resource_conflict(self, e):
        erc = e.response['Error']['Code']
        return (erc == 'ResourceConflictException')

    def is_resource_in_use(self, e):
        erc = e.response['Error']['Code']
        return (erc == 'ResourceInUseException')

    def is_operation_in_progress(self, e):
        erc = e.response['Error']['Code']
        return (erc == 'OperationInProgressException')

    def init_tracker(self, op, id=None, maxSecs=None, policy="ElapsedAndAttempts"):
        sop = self.service_op(op)
        startedAt = time.time()
        return {
            'waitSecs': 1,
            'attempt': 1,
            'op': sop,
            'id': id,
            'maxAttempts': self._maxAttempts,
            'maxSecs': maxSecs,
            'policy': policy,
            'startedAt': startedAt
        }
    
    def retry(self, tracker):
        attempt = tracker['attempt']
        maxAttempts = tracker['maxAttempts']
        maxSecs = tracker['maxSecs']
        policy = tracker['policy']
        elapsedSecs = time.time() - tracker['startedAt']
        if maxSecs:
            elapsedOk = elapsedSecs < maxSecs
        else:
            elapsedOk = True
        if maxAttempts:
            attemptsOk = attempt < maxAttempts
        else:
            attemptsOk = True
        if policy == 'AttemptsOnly': return attemptsOk
        if policy == 'ElapsedOnly': return elapsedOk
        return elapsedOk and attemptsOk
        

    def backoff(self, tracker, limitSecs=-1):
        op = tracker['op']
        id = tracker['id']
        waitSecs = tracker['waitSecs']
        attempt = tracker['attempt']
        logging.info("Will retry rdq operation after backoff interval | Tracker: %s", tracker)
        time.sleep(waitSecs)
        newWait = waitSecs * 2
        if limitSecs > 0:
            newWait = min(newWait, limitSecs)
        newTracker = dict(tracker)
        newTracker['waitSecs'] = newWait
        newTracker['attempt'] = attempt + 1
        return newTracker

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

    def retry_resource_in_use(self, e, tracker):
        canRetry = self.retry(tracker) and self.is_resource_in_use(e)
        if canRetry:
            logging.info("Retry possible after resource in-use error | Detail: %s", e)
        return canRetry

    def retry_operation_in_progress(self, e, tracker):
        canRetry = self.retry(tracker) and self.is_operation_in_progress(e)
        if canRetry:
            logging.info("Retry possible after operation-in-progress error | Detail: %s", e)
        return canRetry

    def new_preview_uuid(self):
        id = str(uuid.uuid4())
        return "00000000-0000-0000-{}".format(id[19:])

    def new_operation_id(self):
        return str(uuid.uuid4())

    def sleep(self, waitSecs):
        time.sleep(waitSecs)

    def to_json(self, src, indent=None):
        if type(src) is str:
            map = json.loads(src)
            return json.dumps(map, indent=indent)
        return json.dumps(src, indent=indent)

    def from_json(self, src):
        if type(src) is str:
            return json.loads(src)
        return src

    def policy_map(self, statements):
        return {
            'Version': "2012-10-17",
            'Statement': statements
        }

    def declare_tags(self, arn, tagsRequired, tagsExisting=None):
        tagsDelta = tagsRequired.subtract(tagsExisting)
        if tagsDelta.isEmpty(): return True
        return self._profile.applyTagsToArn(arn, tagsDelta)

    def info(self, op, argType, argValue, msg, *args):
        sop = self.service_op(op)
        noHead = (argType is None) or (argValue is None)
        argmap = _args_to_map(args)
        if noHead:
            logging.info("%s | Context: %s | Service: %s", msg, argmap, sop)
        else:
            logging.info("%s - %s: %s | Context: %s | Service: %s", msg, argType, argValue, argmap, sop)
        return msg

    def warning(self, op, argType=None, argValue=None, msg="Unspecified", *args):
        sop = self.service_op(op)
        noHead = (argType is None) or (argValue is None)
        argmap = _args_to_map(args)
        ec = {}
        if not noHead: ec[argType] = argValue
        if argmap: ec['Arguments'] = argmap
        logging.warning("%s | Service: %s | Context: %s ", msg, sop, ec)
        return msg

    def fail(self, e, op, argType=None, argValue=None, *args):
        sop = self.service_op(op)
        noHead = (argType is None) or (argValue is None)
        argmap = _args_to_map(args)
        ec = {}
        if not noHead: ec[argType] = argValue
        if argmap: ec['Arguments'] = argmap
        ec['AccountId'] = self._profile.accountId,
        ec['SessionName'] = self._profile.sessionName
        logging.error("%s Client Error | Context: %s | Detail: %s", sop, ec, e)
        if noHead:
            erm = "{} Client Error".format(sop)
        else:
            erm = "{} Client Error for {}: `{}`".format(sop, argType, argValue)
        return erm

    def integrity(self, msg="Unspecified", *args):
        svc = self._service
        argmap = _args_to_map(args)
        ec = {}
        if argmap: ec['Arguments'] = argmap
        ec['AccountId'] = self._profile.accountId,
        ec['SessionName'] = self._profile.sessionName
        logging.error("%s Data Integrity Error | Cause: %s | Context: %s", svc, msg, ec)
        erm = "{} Data Integrity Error: {}".format(svc, msg)
        return erm

    def expired(self, op, argType=None, argValue=None, *args):
        svc = self._service
        noHead = (argType is None) or (argValue is None)
        argmap = _args_to_map(args)
        ec = {}
        if not noHead: ec[argType] = argValue
        if argmap: ec['Arguments'] = argmap
        ec['AccountId'] = self._profile.accountId,
        ec['SessionName'] = self._profile.sessionName
        logging.error("%s Expired | Service: %s | Context: %s", op, svc, ec)
        erm = "{} Expired".format(op)
        return erm

    def preview(self, op, args):
        sop = self.service_op(op)
        return self._profile.preview(sop, args)

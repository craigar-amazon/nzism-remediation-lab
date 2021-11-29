import os
import json
import logging

def initLogging(logLevelVariable='LOGLEVEL', defaultLevel='INFO'):
    levelName = defaultLevel
    if logLevelVariable:
        if logLevelVariable in os.environ:
            varval = os.environ[logLevelVariable]
            if varval:
                levelName = varval[0:1].upper()
    loglevel = logging.INFO
    if levelName == 'D':
        loglevel = logging.DEBUG
    elif levelName == 'W':
        loglevel = logging.WARNING
    elif levelName == 'E':
        loglevel = logging.ERROR
    logging.basicConfig(level=loglevel)
    logging.info("Logging level is %s", logging.getLevelName(loglevel))

class ConfigError(Exception):
    def __init__(self, message):
        self._message = message

    def __str__(self):
        return self._message
    
    @property
    def message(self):
        return self._message

def selectConfig(srcmap, context, aname):
    if not (aname in srcmap):
        msg = "Attribute `{}` is missing from configuration. Context is {}".format(aname, context)
        logging.error(msg)
        raise ConfigError(msg)
    return srcmap[aname]

def normaliseJson(raw, context):
    if type(raw) is str:
        try:
            map = json.loads(raw)
            return json.dumps(map)
        except json.JSONDecodeError as e:
            msg = "Attribute `{}` is not well-formed JSON. Reason is {}".format(context, e)
            logging.error("Maformed JSON in attribute %s | Reason: %s | Input: %s", context, e, raw)
            raise ConfigError(msg)
    return json.dumps(raw, context)

def normaliseInteger(raw, context):
    if type(raw) is int: return raw
    try:
        return int(str(raw))
    except ValueError:
        msg = "Attribute `{}` is not a well-formed Integer. Input is {}".format(context, raw)
        logging.error("Maformed Integer in attribute %s | Input: %s", context, raw)
        raise ConfigError(msg)

def normaliseString(raw, context):
    if type(raw) is str: return raw
    return str(raw)


def _canon_path(pathTuple):
    if len(pathTuple) != 1: return pathTuple
    return pathTuple[0].split('.')

def _update(dst, val, pathTuple):
    if len(pathTuple) == 0: return
    canonTuple = _canon_path(pathTuple)
    _update_tail(dst, canonTuple[0], val, canonTuple[1:])

def _update_tail(dst, key, val, tailTuple):
    isLeaf = len(tailTuple) == 0
    if isLeaf:
        dst[key] = val
    else:
        if not (key in dst):
            dst[key] = {}
        _update_tail(dst[key], tailTuple[0], val, tailTuple[1:])

def _normalise(dst, normMethod, pathTuple):
    if len(pathTuple) == 0: return
    canonTuple = _canon_path(pathTuple)
    _normalise_tail(dst, canonTuple[0], normMethod, canonTuple[1:])

def _normalise_tail(dst, key, normMethod, tailTuple):
    if not (key in dst): return
    isLeaf = len(tailTuple) == 0
    if isLeaf:
        rawVal = dst[key]
        if rawVal:
            normVal = normMethod(rawVal, key)
            dst[key] = normVal
    else:
        _normalise_tail(dst[key], tailTuple[0], normMethod, tailTuple[1:])

def _is_diff(ex, rq, context):
    if (type(ex) is str) and (type(rq) is str): return ex != rq
    if (type(ex) is int) and (type(rq) is int): return ex != rq
    if (type(ex) is bool) and (type(rq) is bool): return ex != rq
    if (type(ex) is dict) and (type(rq) is dict):
        for key in rq:
            newContext = "{}.{}".format(context, key)
            rqVal = rq[key]
            if not (key in ex): return True
            exVal = ex[key]
            if _is_diff(exVal, rqVal, newContext): return True
        for key in ex:
            if not (key in rq): return True
        return False
    
    msg = "Existing value of attribute `{}` is type {}. Specified value is type {}".format(context, type(ex), type(rq))
    logging.error("Type mismatch in attribute `%s` | Existing Type: %s | Specified Type: %s | Existing Value: %s | Specified Value %s", context, type(ex), type(rq), ex, rq)
    raise ConfigError(msg)


class DeltaBuild:
    def __init__(self):
        self._rq = dict()
        self._ex = dict()

    def __str__(self):
        return "required: {}\nexisting: {}".format(json.dumps(self._rq), json.dumps(self._ex))

    def updateRequired(self, map):
        self._rq.update(map) 

    def putRequired(self, val, *path):
        _update(self._rq, val, path)

    def loadExisting(self, ex):
        self._ex.update(ex)

    def normaliseRequired(self, normMethod, *path):
        _normalise(self._rq, normMethod, path)

    def normaliseExisting(self, normMethod, *path):
        _normalise(self._ex, normMethod, path)

    def normaliseRequiredJson(self, *path):
        _normalise(self._rq, normaliseJson, path)

    def normaliseExistingJson(self, *path):
        _normalise(self._ex, normaliseJson, path)

    def required(self):
        return dict(self._rq)

    def delta(self):
        rq = self._rq
        ex = self._ex
        diff = {}
        for key in rq:
            rqVal = rq[key]
            if key in ex:
                exVal = ex[key]
                if _is_diff(exVal, rqVal, key):
                    diff[key] = rqVal
            else:
                diff[key] = rqVal
        return diff

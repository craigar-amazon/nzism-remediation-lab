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
    logger = logging.getLogger()
    logger.setLevel(loglevel)
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

class Tags:
    def __init__(self, tags=None, context=None):
        self._map = {}
        self.update(tags, context)

    def isEmpty(self):
        return len(self._map) == 0

    def notEmpty(self):
        return len(self._map) > 0

    def put(self, kwd, value):
        self._map[kwd] = str(value)

    def putAll(self, **kwargs):
        for kwd in kwargs:
            self._map[kwd] = str(kwargs[kwd])

    def get(self, kwd):
        return self._map.get(kwd)

    def update(self, tags, context=None):
        if not tags: return
        if isinstance(tags, Tags):
            self.updateDict(tags._map)
        elif type(tags) is list:
            self.updateList(tags)
        elif type(tags) is dict:
            self.updateDict(tags)
        else:
            msg = "Unsupported tag format {}".format(type(tags))
            if context:
                msg = msg + " used by attribute " + context
            logging.error(msg)
            raise ConfigError(msg)

    def updateList(self, rlist, prefix=""):
        if not rlist: return
        kk = "{}Key".format(prefix)
        kv = "{}Value".format(prefix)
        rmap = dict()
        for rtag in rlist:
            if not (type(rtag) is dict): continue
            if not (kk in rtag): continue
            if not (kv in rtag): continue
            rkey = rtag[kk]
            if not (type(rkey) is str): continue
            if len(rkey) == 0: continue
            rval = rtag[kv]
            rmap[rkey] = str(rval)
        self._map.update(rmap)

    def updateDict(self, rdict):
        if not rdict: return
        for kwd in rdict:
            self._map[kwd] = str(rdict[kwd])

    def subtract(self, tags):
        lmap = self._map
        if tags:
            rmap = tags._map
            result = dict()
            for lkey in lmap:
                delta = False
                if lkey in rmap:
                    lval = lmap[lkey]
                    rval = rmap[lkey]
                    delta = lval != rval
                else:
                    delta = True
                if delta:
                    result[lkey] = lmap[lkey]
        else:
            result = dict(lmap)
        newTags = Tags()
        newTags._map = result
        return newTags

    def toList(self, prefix=""):
        kk = "{}Key".format(prefix)
        kv = "{}Value".format(prefix)
        sk = sorted(self._map.keys())
        r = list()
        for k in sk:
            v = self._map[k]
            tag = {}
            tag[kk] = k
            tag[kv] = v
            r.append(tag)
        return r

    def toDict(self):
        return dict(self._map)

    def equalsDict(self, rmap):
        lmap = self._map
        lkeys = sorted(lmap.keys())
        rkeys = sorted(rmap.keys())
        if len(lkeys) != len(rkeys): return False
        count = len(lkeys)
        for i in range(count):
            lkey = lkeys[i]
            rkey = rkeys[i]
            if lkey != rkey: return False
            lval = lmap[lkey]
            rval = rmap[rkey]
            if lval != rval: return False
        return True

    def __str__(self):
        return json.dumps(self._map)

    def __eq__(self, rhs):
        if isinstance(rhs, Tags):
            return self.equalsDict(rhs._map)
        if type(rhs) is dict:
            return self.equalsDict(rhs)
        return False


def normaliseJson(raw, context):
    indent = 2
    if type(raw) is str:
        try:
            map = json.loads(raw)
            return json.dumps(map, indent=indent)
        except json.JSONDecodeError as e:
            msg = "Attribute `{}` is not well-formed JSON. Reason is {}".format(context, e)
            logging.error("Malformed JSON in attribute %s | Reason: %s | Input: %s", context, e, raw)
            raise ConfigError(msg)
    return json.dumps(raw, indent=indent)

def normaliseList(raw, context):
    if not (type(raw) is list):
        msg = "Attribute `{}` is not a List. Type is {}".format(context, type(raw))
        logging.error("Expecting List in attribute %s", context)
        raise ConfigError(msg)
    return sorted(raw)

def normaliseTags(raw, context):
    return Tags(raw, context)

def normaliseInteger(raw, context):
    if type(raw) is int: return raw
    try:
        return int(str(raw))
    except ValueError:
        msg = "Attribute `{}` is not a well-formed Integer. Input is {}".format(context, raw)
        logging.error("Malformed Integer in attribute %s | Input: %s", context, raw)
        raise ConfigError(msg)

def normaliseString(raw, context):
    if type(raw) is str: return raw
    return str(raw)


def _canon_path(path):
    return path.split('.')

def _update(dst, path, val):
    canonPath = _canon_path(path)
    if len(canonPath) == 0: return
    _update_tail(dst, canonPath[0], val, canonPath[1:])

def _update_tail(dst, key, val, tailPath):
    isLeaf = len(tailPath) == 0
    if isLeaf:
        dst[key] = val
    else:
        if not (key in dst):
            dst[key] = {}
        _update_tail(dst[key], tailPath[0], val, tailPath[1:])

def _normalise(dst, path, normMethod):
    canonPath = _canon_path(path)
    if len(canonPath) == 0: return
    _normalise_tail(dst, canonPath[0], normMethod, canonPath[1:])

def _normalise_tail(dst, key, normMethod, tailPath):
    if not (key in dst): return
    isLeaf = len(tailPath) == 0
    if isLeaf:
        rawVal = dst[key]
        if rawVal:
            normVal = normMethod(rawVal, key)
            dst[key] = normVal
    else:
        _normalise_tail(dst[key], tailPath[0], normMethod, tailPath[1:])

def _is_diff(ex, rq, context):
    if (type(ex) is str) and (type(rq) is str): return ex != rq
    if (type(ex) is int) and (type(rq) is int): return ex != rq
    if (type(ex) is bool) and (type(rq) is bool): return ex != rq
    if (type(ex) is Tags) and (type(rq) is Tags): return ex != rq
    if (type(ex) is list) and (type(rq) is list):
        exlen = len(ex)
        rqlen = len(rq)
        if exlen != rqlen: return True
        for i in range(rqlen):
            newContext = "{}[{}]".format(context, i)
            if _is_diff(ex[i], rq[i], newContext): return True
        return False
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

    def putRequired(self, path, val):
        _update(self._rq, path, val)

    def putRequiredJson(self, path, val):
        _update(self._rq, path, normaliseJson(val, path))

    def putRequiredList(self, path, val):
        _update(self._rq, path, normaliseList(val, path))

    def putRequiredString(self, path, val):
        _update(self._rq, path, normaliseString(val, path))

    def loadExisting(self, ex):
        self._ex.update(ex)

    def normaliseRequired(self, path, normMethod):
        _normalise(self._rq, path, normMethod)

    def normaliseExisting(self, path, normMethod):
        _normalise(self._ex, path, normMethod)

    def normaliseRequiredJson(self, path):
        _normalise(self._rq, path, normaliseJson)

    def normaliseExistingJson(self, path):
        _normalise(self._ex, path, normaliseJson)

    def normaliseRequiredList(self, path):
        _normalise(self._rq, path, normaliseList)

    def normaliseExistingList(self, path):
        _normalise(self._ex, path, normaliseList)

    def normaliseRequiredInteger(self, path):
        _normalise(self._rq, path, normaliseInteger)

    def normaliseExistingInteger(self, path):
        _normalise(self._ex, path, normaliseInteger)

    def normaliseRequiredString(self, path):
        _normalise(self._rq, path, normaliseString)

    def normaliseExistingString(self, path):
        _normalise(self._ex, path, normaliseString)

    def normaliseExistingTags(self, path):
        _normalise(self._ex, path, normaliseTags)

    def required(self):
        return dict(self._rq)

    def requiredKeys(self):
        return list(self._rq.keys())

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


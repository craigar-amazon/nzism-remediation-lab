import logging

class RetryError(Exception):
    def __init__(self, message):
        self._message = message

    def __str__(self):
        return self._message
    
    @property
    def message(self):
        return self._message

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

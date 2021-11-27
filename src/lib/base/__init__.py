import os
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

from typing import List
import logging
from lib.rdq import Profile

from lib.base import initLogging
from lib.lambdas.core.dispatcher import Dispatcher

def lambda_handler(event, context):
    initLogging()
    try:
        profile = Profile()
        dispatcher = Dispatcher(profile)
        dispatcher.dispatch(event)
    except Exception as e:
        syn = str(type(e))
        msg = str(e)
        report = {'Synopsis': syn, 'Context': "Main handler", 'Cause': msg, 'Event': event}
        logging.exception(report)
        raise


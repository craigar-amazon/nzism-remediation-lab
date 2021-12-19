import logging

import cfg.core as cfgCore
import lib.base.ruleresponse as rr
from lib.base.request import DispatchEvent

from lib.rdq import Profile
from lib.rdq.svccwm import CwmClient


class Analyzer:
    def __init__(self, profile :Profile):
        self._profile = profile
        self._cwmclient = CwmClient(profile)

    def analyzeResponse(self, functionName, event :DispatchEvent, response :dict):
        statusCode = response['StatusCode']
        payload = response['Payload']
        if statusCode != 200:
            syn = "Function {} returned status code {}".format(functionName, statusCode)
            report = {'Synopsis': syn, 'Response': response, 'Event': event.toDict()}
            logging.error(report)
            return "retry"

        ar = rr.ActionResponse(source=payload)
        action = ar.action
        cwNamespace = cfgCore.coreCloudWatchNamespace(action)
        cwMetric = "{}.{}".format(ar.major, ar.minor)
        target = event['target']
        cwDimensionMap = {
            'configRuleName': event['configRuleName'],
            'regionName': target['awsRegion'],
            'accountName': target['awsAccountName']
        }
        self._cwmclient.putCount(cwNamespace, cwMetric, cwDimensionMap)

        if ar.isTimeout:
            syn = "Function {} Timeout".format(functionName)
            report = {'Synopsis': syn, 'Response': ar.toDict(), 'Event': event.toDict()}
            logging.error(report)
            return "retry"

        if event.preview:
            syn = "Function {} Preview".format(functionName)
            report = {'Synopsis': syn, 'Preview': ar.preview}
            logging.warning(report)

        if ar.isSuccess:
            syn = "Function {} Succeeded".format(functionName)
            report = {'Synopsis': syn, 'Response': ar.toDict(), 'Event': event.toDict()}
            logging.info(report)
            return "done"
        
        syn = "Function {} Failed".format(functionName)
        report = {'Synopsis': syn, 'Response': ar.toDict(), 'Event': event.toDict()}
        logging.error(report)
        return "failed"

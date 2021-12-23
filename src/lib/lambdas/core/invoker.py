import logging

import cfg.core as cfgCore
import lib.base.ruleresponse as rr
from lib.base.request import DispatchEvent

from lib.rdq import Profile
from lib.rdq.svccwm import CwmClient
import lib.lambdas.core.cwdims as cwdims



class Invoker:
    def __init__(self, profile :Profile):
        self._profile = profile
        self._cwmclient = CwmClient(profile)

    def publish_cloudwatch_metrics(self, functionName, event :DispatchEvent, ar :rr.ActionResponse):
        action = ar.action
        cwNamespace = cfgCore.coreCloudWatchNamespace(action)
        cwMetric = "{}.{}".format(ar.major, ar.minor)
        dimensionMaps = cwdims.getDimensionMaps(event)
        for dimensionMap in dimensionMaps:
            self._cwmclient.putCount(cwNamespace, cwMetric, dimensionMap)

    def publish_preview(self, functionName, event :DispatchEvent, ar :rr.ActionResponse):
        if not event.preview: return

        syn = "Function {} Preview".format(functionName)
        report = {'Synopsis': syn, 'Preview': ar.preview}
        logging.warning(report)


    def analyze_response(self, functionName, event :DispatchEvent, response :dict):
        statusCode = response['StatusCode']
        payload = response['Payload']
        if statusCode != 200:
            syn = "Function {} returned status code {}".format(functionName, statusCode)
            report = {'Synopsis': syn, 'Response': response, 'Event': event.toDict()}
            logging.error(report)
            return "retry"

        ar = rr.ActionResponse(source=payload)
        self.publish_cloudwatch_metrics(functionName, event, ar)

        if ar.isTimeout:
            syn = "Function {} Timeout".format(functionName)
            report = {'Synopsis': syn, 'Response': ar.toDict(), 'Event': event.toDict()}
            logging.error(report)
            return "retry"

        self.publish_preview(functionName, event, ar)

        if ar.isSuccess:
            syn = "Function {} Succeeded".format(functionName)
            report = {'Synopsis': syn, 'Response': ar.toDict(), 'Event': event.toDict()}
            logging.info(report)
            return "done"
        
        syn = "Function {} Failed".format(functionName)
        report = {'Synopsis': syn, 'Response': ar.toDict(), 'Event': event.toDict()}
        logging.error(report)
        return "failed"


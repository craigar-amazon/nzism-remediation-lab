import logging

import lib.base.ruleresponse as rr

def analyzeResponse(functionName, event :dict, response :dict):
    statusCode = response['StatusCode']
    payload = response['Payload']
    if statusCode != 200:
        msg = "Function {} returned status code {}".format(functionName, statusCode)
        logging.error("%s | Event: %s | Response: %s", msg, event, response)
        return "retry"

    ar = rr.ActionResponse(source=payload)
    if ar.isTimeout():
        head = "Function {} Timeout".format(functionName)
        logging.error("%s | Response: %s | Event: %s", head, ar.toDict(), event)
        return "retry"

    isPreview = event['preview']
    if isPreview:
        preview = ar.preview()
        msg = "Function {} Preview".format(functionName)
        logging.warning("%s | Result: %s", msg, preview)

    if ar.isSuccess():
        head = "Function {} Succeeded".format(functionName)
        logging.info("%s | Response: %s | Event: %s", head, ar.toDict(), event)
        return "done"
    
    head = "Function {} Failed".format(functionName)
    logging.info("%s | Response: %s | Event: %s", head, ar.toDict(), event)
    return "failed"

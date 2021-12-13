import logging

import lib.base.ruleresponse as rr

def analyzeResponse(functionName, event, response):
    target = event['target']
    statusCode = response['StatusCode']
    payload = response['Payload']
    if statusCode != 200:
        msg = "Function {} returned status code {}".format(functionName, statusCode)
        logging.error("%s | Event: %s | Response: %s", msg, event, response)
        return "retry"

    r = rr.ActionResponse(source=payload)
    if r.isTimeout():
        head = "Function {} Timeout".format(functionName)
        logging.error("%s | Action: %s | Reason: %s | Message: %s | Target: %s", head, r.action(), r.minor(), r.message(), target)
        return "retry"

    isPreview = event['preview']
    if isPreview:
        preview = response.preview()
        msg = "Function {} Preview".format(functionName)
        logging.warning("%s | Result: %s", msg, preview)

    if r.isSuccess():
        head = "Function {} Succeeded".format(functionName)
        logging.info("%s | Action: %s | Result: %s | Message: %s | Target: %s", head, r.action(), r.minor(), r.message(), target)
        return "done"
    
    head = "Function {} Failed".format(functionName)
    logging.error("%s | Action: %s | Reason: %s | Message: %s | Target: %s", head, r.action(), r.minor(), r.message(), target)
    return "failed"

import logging

from lib.core import RetryError

def analyzeResponse(functionName, event, response):
    statusCode = response['StatusCode']
    payload = response['Payload']
    if statusCode != 200:
        msg = "Function {} returned status code {}".format(functionName, statusCode)
        logging.error("%s | Event: %s | Response: %s", msg, event, response)
        raise RetryError(msg)

    reason = 'errorMessage'
    if reason in payload:
        erm = payload[reason]
        msg = "Function {} returned error: {}".format(functionName, erm)
        logging.error("%s | Event: %s | Response: %s", msg, event, response)
        raise RetryError(msg)

    reason = 'remediationFailure'
    if reason in payload:
        erm = payload[reason]
        msg = "Function {} returned remediation error: {}".format(functionName, erm)
        logging.error("%s | Event: %s", msg, event)
        raise RetryError(msg)

    isPreview = event['preview']
    if isPreview:
        msg = "Function {} Preview".format(functionName)
        logging.warning("%s | Result: %s", msg, payload)
    else:
        msg = "Function {} Succeeded".format(functionName)
        logging.info("%s | Result: %s", msg, payload)

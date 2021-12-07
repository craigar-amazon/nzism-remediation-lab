import logging

from lib.lambdas import RetryError

def analyzeResponse(functionName, event, response):
    statusCode = response['StatusCode']
    payload = response['Payload']
    if statusCode != 200:
        msg = "Function {} returned status code {}".format(functionName, statusCode)
        logging.error("%s | Event: %s | Response: %s", msg, event, response)
        raise RetryError(msg)

    erm = payload.get('errorMessage')
    if erm:
        msg = "Function {} returned error: {}".format(functionName, erm)
        logging.error("%s | Event: %s | Response: %s", msg, event, response)
        raise RetryError(msg)

    erm = payload.get('remediationFailure')
    if erm:
        msg = "Function {} returned remediation failure: {}".format(functionName, erm)
        logging.error("%s | Event: %s", msg, event)
        raise RetryError(msg)

    erm = payload.get('remediationTimeout')
    if erm:
        msg = "Function {} returned remediation timeout: {}".format(functionName, erm)
        logging.warning("%s | Event: %s", msg, event)
        raise RetryError(msg)

    isPreview = event['preview']
    if isPreview:
        msg = "Function {} Preview".format(functionName)
        logging.warning("%s | Result: %s", msg, payload)
    else:
        msg = "Function {} Succeeded".format(functionName)
        logging.info("%s | Result: %s", msg, payload)

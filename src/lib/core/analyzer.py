import logging

from lib.core import RetryError

def analyzeResponse(functionName, event, response):
    statusCode = response['StatusCode']
    payload = response['Payload']
    if statusCode != 200:
        msg = "Function {} returned status code {}".format(functionName, statusCode)
        logging.error(msg, event, response)
        raise RetryError(msg)

    reason = 'errorMessage'
    if reason in payload:
        erm = payload[reason]
        msg = "Function {} returned error: {}".format(functionName, erm)
        logging.error(msg, event, payload)
        raise RetryError(msg)

    reason = 'remediationFailure'
    if reason in payload:
        erm = payload[reason]
        msg = "Function {} returned remediation error: {}".format(functionName, erm)
        logging.error(msg, event)
        raise RetryError(msg)

    msg = "Function {} succeeded".format(functionName)
    logging.info(msg, payload)

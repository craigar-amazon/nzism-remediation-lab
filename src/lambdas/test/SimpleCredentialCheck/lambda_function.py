import report

def lambda_handler(event, context):
    (success, msg, body) = handler(event)
    if (success):
        print("Success: "+msg)
    else:
        print("Failed: "+msg)
    statusCode = 200 if success else 500
    return {
        'statusCode': statusCode,
        'message': msg,
        'body': body
    }

def handler(event):
    response = {
        "input": event,
        "output": report.accountInfo(event)
    }
    return (True, "Done", response)

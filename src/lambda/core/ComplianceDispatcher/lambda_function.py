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
    if not ("source" in event):
        return (False, "Missing source attribute", {})

    source = event["source"]
    if source == "aws.config": 
        return handlerConfig(event)

    return (False, "Unsupported source: "+source, {})

def handlerConfig(event):
    print(event)
    return (True, "Done", {})

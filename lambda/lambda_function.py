def lambda_handler(event, context):
    (success, msg) = handler(event)
    if (success):
        print("Success: "+msg)
    else:
        print("Failed: "+msg)
    statusCode = 200 if success else 500
    return {
        'statusCode': statusCode,
        'body': msg
    }

def handler(event):
    if not ("source" in event):
        return (False, "Missing source attribute")

    source = event["source"]
    if source == "aws.config": 
        return (True, "Done")

    return (False, "Unsupported source: "+source)

import boto3

from utils.util_sts import assumeRole

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
        return (True, "Done", {})

    if source == "installer":
        return handlerInstaller(event)

    return (False, "Unsupported source: "+source, {})

def handlerInstaller(event):
    homeSession = boto3.session.Session()
    appSession = assumeRole(homeSession, 'arn:aws:iam::119399605612:role/aws-controltower-AdministratorExecutionRole', 'app1')
    s3_client = appSession.client('s3')
    response = s3_client.list_buckets()
    buckets = response['Buckets']
    bucketNames = []
    for bucket in buckets:
        bucketNames.append(bucket['Name'])
    return (True, "AssumedRole", bucketNames)
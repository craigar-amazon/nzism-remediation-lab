
from event import complianceChangeEventHandler
from scan import scanCloudwatchLogGroups, scanS3Buckets


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
        return handler_config(event)

    if source == "scan":
        return handler_scan(event)

    return (False, "Unsupported source: "+source)


def handler_config(event):
    detail_type = event["detail-type"]
    if detail_type == "Config Rules Compliance Change":
        return complianceChangeEventHandler(event)

    return (True, "No action - "+detail_type)

def handler_scan(event):
    resource = event['resource'] if 'resource' in event else 'all'
    results = []
    if resource == 'all' or resource == 'CloudwatchLogGroups':
        results.append(scanCloudwatchLogGroups(event))
    if resource == 'all' or resource == 'S3Buckets':
        results.append(scanS3Buckets(event))
    return (True, '|'.join(results))

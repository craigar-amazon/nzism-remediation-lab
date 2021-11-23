def lambda_handler(event, context):
    records = event['Records']
    for record in records:
        print(record)
        
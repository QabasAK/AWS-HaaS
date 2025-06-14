import json

def lambda_handler(event, context):
    for record in event['Records']:
        if record['eventName'] == 'INSERT':
            new_image = record['dynamodb']['NewImage']
            print("New insert into CowrieLogs:")
            for key, val in new_image.items():
                print(f"   {key}: {list(val.values())[0]}")
    return {'statusCode': 200}

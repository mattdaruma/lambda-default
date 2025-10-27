import json

def lambda_handler(event, context):
    print("default event:", event)
    return {
        'statusCode': 200,
        'body': json.dumps('Message received.')
    }

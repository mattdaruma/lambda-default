import boto3
import json
import os

TABLE_NAME = 'moyabe-connections'
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    print("default event:", event)
    connection_id = event.get('requestContext', {}).get('connectionId')
    
    try:
        # Get the sender's username
        response = table.get_item(Key={'connectionId': connection_id})
        username = response.get('Item', {}).get('username', 'anonymous')

        # Get the message from the event body
        message_body = json.loads(event.get('body', '{}'))
        message = message_body.get('message')

        if not message:
            return {'statusCode': 400, 'body': 'Message content is required.'}

        # Get all active connections
        response = table.scan(ProjectionExpression='connectionId')
        connections = response.get('Items', [])

        # Construct the message payload
        payload = json.dumps({'sender': username, 'message': message})

        # Get the API Gateway management client
        domain_name = event.get('requestContext', {}).get('domainName')
        stage = event.get('requestContext', {}).get('stage')
        endpoint_url = f'https://{domain_name}/{stage}'
        apigw_management = boto3.client('apigatewaymanagementapi', endpoint_url=endpoint_url)

        # Broadcast the message to all connections
        for connection in connections:
            conn_id = connection['connectionId']
            if conn_id != connection_id:
                try:
                    apigw_management.post_to_connection(ConnectionId=conn_id, Data=payload)
                except apigw_management.exceptions.GoneException:
                    # Stale connection, delete it from the table
                    print(f"Stale connection {conn_id}, deleting.")
                    table.delete_item(Key={'connectionId': conn_id})

        return {'statusCode': 200, 'body': 'Message sent.'}

    except Exception as e:
        print(f"Error: {e}")
        return {'statusCode': 500, 'body': 'Internal server error'}
import os
import boto3
import json
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['USER_TABLE_NAME'])

def handler(event, context):
    try:
        # Extract user attributes from the Cognito event
        user_attributes = event['request']['userAttributes']
        
        # Create user record
        user_item = {
            'userId': user_attributes['sub'],  # Cognito generated unique ID
            'email': user_attributes['email'],
            'email_verified': user_attributes['email_verified'],
            'created_at': datetime.now().isoformat(),
            'cognito_username': event['userName']
        }

        # Add optional attributes if they exist
        if 'given_name' in user_attributes:
            user_item['first_name'] = user_attributes['given_name']
        if 'family_name' in user_attributes:
            user_item['last_name'] = user_attributes['family_name']
        if 'phone_number' in user_attributes:
            user_item['phone_number'] = user_attributes['phone_number']

        # Write to DynamoDB
        table.put_item(Item=user_item)
        
        print(f"Successfully created user record for {user_item['email']}")
        
        # Return the event object back to Cognito
        return event
        
    except Exception as e:
        print(f"Error creating user record: {str(e)}")
        raise e
import boto3
import os
import json
import logging
from botocore.exceptions import ClientError
import jwt
import requests


cognito_client = boto3.client('cognito-idp')

USER_POOL_ID = os.environ['USER_POOL_ID']
COGNITO_REGION = "us-east-2"
secret_name = "prod/yami/clientId"

session = boto3.session.Session()
client = session.client(
    service_name='secretsmanager',
    region_name=COGNITO_REGION
)

try:
    get_secret_value_response = client.get_secret_value(
        SecretId=secret_name
    )
except ClientError as e:
    raise e

CLIENT_ID = get_secret_value_response['SecretString']


def verify_token(token):
    """Verify JWT token and extract claims."""
    try:
        header = jwt.get_unverified_header(token)
        kid = header["kid"]
        
        # Fetch Cognito public keys
        keys_url = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json"
        response = requests.get(keys_url)
        response.raise_for_status()
        keys = response.json()["keys"]
        
        key = next((k for k in keys if k["kid"] == kid), None)
        if not key:
            raise Exception("Public key not found.")

        claims = jwt.decode(token, algorithms=["RS256"], options={"verify_signature": False})
        return claims

    except jwt.ExpiredSignatureError:
        print("Token has expired")
        return None
    except Exception as e:
        print(f"Token verification failed: {str(e)}")
        return None
    


def handler(event, context):
    try:

        headers = event.get("headers", {})
        token = headers.get("Authorization", "").replace("Bearer ", "")
        
        if not token:
            return {"statusCode": 401, "body": json.dumps({"error": "Unauthorized"})}
        
        
        claims = verify_token(token)
        if not claims:
            return {"statusCode": 403, "body": json.dumps({"error": "Invalid token"})}
        
        username = claims.get("cognito:username")
        user_groups = claims.get("cognito:groups", [])

        if "Admins" not in user_groups:
            return {"statusCode": 403, "body": json.dumps({"error": "Access Denied. Admins only."})}
        
        # Parse the request body
        body = json.loads(event['body'])
        user_id = body.get('userId')
        group_name = body.get('groupName')

        if not user_id or not group_name:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Missing userId or groupName in request"})
            }

        # Add user to the specified group
        response = cognito_client.admin_add_user_to_group(
            UserPoolId=USER_POOL_ID,
            Username=user_id,
            GroupName=group_name
        )

        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",  # Allow all origins
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization"
            },
            "body": json.dumps({
                "message": f"User {user_id} added to group {group_name}",
                "response": response
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({"error": str(e)})
        }

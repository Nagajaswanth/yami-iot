import boto3
import os
import json
import logging
from botocore.exceptions import ClientError
import jwt
import requests

USER_POOL_ID = os.environ['USER_POOL_ID']
cognito_client = boto3.client('cognito-idp')
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

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def verify_token(token):
    """Verify JWT token and extract claims."""
    logger.info("Lambda function started")
    logger.info(f"PyJWT version: {jwt.__version__}")
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
    

def list_users_in_group(group_name):
    """Fetch users belonging to a specific group."""
    users = []
    response = cognito_client.list_users_in_group(UserPoolId=USER_POOL_ID, GroupName=group_name)
    while response:
        users.extend(response.get('Users', []))
        response = cognito_client.list_users_in_group(
            UserPoolId=USER_POOL_ID,
            GroupName=group_name,
            NextToken=response.get('NextToken')
        ) if 'NextToken' in response else None
    return users

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

        # Fetch all users from Cognito
        all_users = cognito_client.list_users(UserPoolId=USER_POOL_ID)['Users']

        # Fetch users from each role
        admin_users = list_users_in_group("Admins")
        dev_users = list_users_in_group("Devs")
        user_users = list_users_in_group("Users")

        # Create a set of users who belong to a group
        assigned_user_ids = {user['Username'] for user in admin_users + dev_users + user_users}

        # Separate users into assigned and unassigned
        users_with_roles = [
            {"userId": user['Username'], "email": next(attr['Value'] for attr in user['Attributes'] if attr['Name'] == 'email'), "role": "Admin"}
            for user in admin_users
        ] + [
            {"userId": user['Username'], "email": next(attr['Value'] for attr in user['Attributes'] if attr['Name'] == 'email'), "role": "Dev"}
            for user in dev_users
        ] + [
            {"userId": user['Username'], "email": next(attr['Value'] for attr in user['Attributes'] if attr['Name'] == 'email'), "role": "User"}
            for user in user_users
        ]

        users_without_roles = [
            {"userId": user['Username'], "email": next(attr['Value'] for attr in user['Attributes'] if attr['Name'] == 'email')}
            for user in all_users if user['Username'] not in assigned_user_ids
        ]

        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",  # Allow all origins
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization"
            },
            "body": json.dumps({
                "usersWithRoles": users_with_roles,
                "usersWithoutRoles": users_without_roles
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

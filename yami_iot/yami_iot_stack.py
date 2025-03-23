from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_cognito as cognito,
    aws_dynamodb as dynamodb,
    aws_iam as iam
)
from constructs import Construct

class YamiIotStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create DynamoDB table
        user_table = dynamodb.Table(
            self, 'UserTable',
            partition_key=dynamodb.Attribute(
                name='userId',
                type=dynamodb.AttributeType.STRING
            )
        )

        # Create Lambda function
        user_sync_lambda = _lambda.Function(
            self, 'UserSyncLambda',
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler='handler.handler',
            code=_lambda.Code.from_asset('lambda'),
            environment={
                'USER_TABLE_NAME': user_table.table_name
            }
        )

        # Grant DynamoDB permissions to Lambda
        user_table.grant_write_data(user_sync_lambda)

        # Create Cognito User Pool
        user_pool = cognito.UserPool(
            self, 'UserPool',
            self_sign_up_enabled=True,
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(required=True),
                given_name=cognito.StandardAttribute(required=True),
                family_name=cognito.StandardAttribute(required=True)
            ),
            # Configure the Lambda trigger
            lambda_triggers=cognito.UserPoolTriggers(
                post_confirmation=user_sync_lambda
            )
        )

        user_pool_client = user_pool.add_client(
            'UserPoolClient',
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True
            ),
            prevent_user_existence_errors=True
        )

        # Grant Cognito permissions to invoke Lambda
        user_sync_lambda.add_permission(
            'CognitoInvokeLambda',
            principal=iam.ServicePrincipal('cognito-idp.amazonaws.com'),
            source_arn=user_pool.user_pool_arn
        )
        
        CfnOutput(self, "UserPoolId", value=user_pool.user_pool_id)
        CfnOutput(self, "UserPoolClientId", value=user_pool_client.user_pool_client_id)
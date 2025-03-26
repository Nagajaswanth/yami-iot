from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_cognito as cognito,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_apigateway as apigateway,
    CfnOutput,
    aws_secretsmanager as secretsmanager
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
                given_name=cognito.StandardAttribute(required=True)
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

        # Create Cognito User Groups
        admin_group = cognito.CfnUserPoolGroup(self, "AdminsGroup",
            user_pool_id=user_pool.user_pool_id,
            group_name="Admins",
            description="Administrators with full access"
        )

        dev_group = cognito.CfnUserPoolGroup(self, "DevsGroup",
            user_pool_id=user_pool.user_pool_id,
            group_name="Devs",
            description="Developers with limited access"
        )

        user_group = cognito.CfnUserPoolGroup(self, "UsersGroup",
            user_pool_id=user_pool.user_pool_id,
            group_name="Users",
            description="Regular users with basic access"
        )

        # Grant Cognito permissions to invoke Lambda
        user_sync_lambda.add_permission(
            'CognitoInvokeLambda',
            principal=iam.ServicePrincipal('cognito-idp.amazonaws.com'),
            source_arn=user_pool.user_pool_arn
        )

        lambda_layer = _lambda.LayerVersion(
            self, 'LambdaLayer',
            code=_lambda.Code.from_asset('lambda_layer'),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_9]
        )

        my_secret = secretsmanager.Secret.from_secret_name_v2(self, "MySecret", "prod/yami/clientId")

        assign_role_lambda = _lambda.Function(
            self, 'AssignRoleLambda',
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler='assign_role.handler',
            code=_lambda.Code.from_asset('lambda'),
            environment={
                'USER_POOL_ID': user_pool.user_pool_id
            },
            layers=[lambda_layer]
        )

        # Grant permission to Lambda for Cognito user management
        assign_role_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=["cognito-idp:AdminAddUserToGroup"],
            resources=[user_pool.user_pool_arn]
        ))
        my_secret.grant_read(assign_role_lambda)

        authorizer = apigateway.CognitoUserPoolsAuthorizer(
            self, "APIAuthorizer",
            cognito_user_pools=[user_pool]
        )


        api = apigateway.RestApi(self, "UserManagementAPI",
            rest_api_name="User Management Service",
            description="API for managing users and roles"
        )

        # Create API resource for assigning roles
        assign_role_resource = api.root.add_resource("assign-role")
        assign_role_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(assign_role_lambda),
            authorization_type=apigateway.AuthorizationType.COGNITO,
            authorizer=authorizer,
            )

        
        fetch_users_lambda = _lambda.Function(
            self, 'FetchUsersLambda',
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler='fetch_users.handler',
            code=_lambda.Code.from_asset('lambda'),
            environment={
                'USER_POOL_ID': user_pool.user_pool_id
            },
            layers=[lambda_layer]
        )

        fetch_users_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=["cognito-idp:ListUsers", "cognito-idp:ListUsersInGroup"],
            resources=[user_pool.user_pool_arn]
        ))
        my_secret.grant_read(fetch_users_lambda)
        
        fetch_users_resource = api.root.add_resource("fetch-users")
        fetch_users_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(fetch_users_lambda),
            authorization_type=apigateway.AuthorizationType.COGNITO,
            authorizer=authorizer
        )
        
        CfnOutput(self, "UserPoolId", value=user_pool.user_pool_id)
        CfnOutput(self, "UserPoolClientId", value=user_pool_client.user_pool_client_id)
        CfnOutput(self, "ApiEndpoint", value=api.url)
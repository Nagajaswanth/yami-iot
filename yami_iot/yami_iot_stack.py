import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_cognito as cognito,
    aws_iam as iam,
    aws_lambda as _lambda,
)
from constructs import Construct


class YamiIotStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        users_user_pool = cognito.UserPool(
            self,
            "UsersUserPool",
            user_pool_name="Users-Pool",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(
                username=True,
                email=True
            ),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True
            ),
            # account_recovery=cognito.AccountRecovery.EMAIL_ONLY, # Example if needed
        )

        users_user_pool_client = cognito.UserPoolClient(
            self,
            "UsersUserPoolClient",
            user_pool=users_user_pool,
            generate_secret=False,
            supported_identity_providers=[
                cognito.UserPoolClientIdentityProvider.COGNITO
            ],
        )

        admins_user_pool = cognito.UserPool(
            self,
            "AdminsUserPool",
            user_pool_name="Admins-Pool",
            self_sign_up_enabled=False,  # Typically, admins are invited
            sign_in_aliases=cognito.SignInAliases(
                username=True,
                email=True
            ),
            password_policy=cognito.PasswordPolicy(
                min_length=10,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True
            )
        )

        admins_user_pool_client = cognito.UserPoolClient(
            self,
            "AdminsUserPoolClient",
            user_pool=admins_user_pool,
            generate_secret=False,
            supported_identity_providers=[
                cognito.UserPoolClientIdentityProvider.COGNITO
            ],
        )

        devs_user_pool = cognito.UserPool(
            self,
            "DevelopersUserPool",
            user_pool_name="Developers-Pool",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(
                username=True,
                email=True
            ),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=False,
                require_symbols=False,
                require_digits=True
            )
        )

        devs_user_pool_client = cognito.UserPoolClient(
            self,
            "DevelopersUserPoolClient",
            user_pool=devs_user_pool,
            generate_secret=False,
            supported_identity_providers=[
                cognito.UserPoolClientIdentityProvider.COGNITO
            ],
        )


        cdk.Stack.of(self).export_value(
            users_user_pool.user_pool_arn, name="UsersUserPoolArn"
        )
        cdk.Stack.of(self).export_value(
            admins_user_pool.user_pool_arn, name="AdminsUserPoolArn"
        )
        cdk.Stack.of(self).export_value(
            devs_user_pool.user_pool_arn, name="DevelopersUserPoolArn"
        )

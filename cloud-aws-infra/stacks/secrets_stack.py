from aws_cdk import (
    Stack,
    aws_secretsmanager as secretsmanager,
    SecretValue as secret_value,
)
from constructs import Construct

from .utils.utilities import formulate_resource_id
from .utils.config_constants import Constants


class SecretsStack(Stack):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        env = self.node.try_get_context(
            Constants.DEPLOYMENT_ENVIRONMENT_KEY
        )

        # =========================================================
        # DATABASE SECRET
        # =========================================================
        # Mirrors future Kubernetes Secret:
        #
        # DB_NAME
        # DB_USERNAME
        # DB_PASSWORD
        #
        # Values can be injected later via GitHub Actions
        # =========================================================
        self.db_secret = secretsmanager.Secret(
            self,
            formulate_resource_id(self, "DatabaseSecret"),
            secret_name=f"/ridelist/{env}/database",
            description=f"RideList database credentials for {env}",
            secret_object_value={
                "DB_NAME": secret_value.unsafe_plain_text(""),
                "DB_USERNAME": secret_value.unsafe_plain_text(""),
                "DB_PASSWORD": secret_value.unsafe_plain_text(""),
            },
        )

        # =========================================================
        # JWT SECRET
        # =========================================================
        # JWT_SECRET generated automatically
        # Expiration values included for env parity
        # =========================================================
        self.jwt_secret = secretsmanager.Secret(
            self,
            formulate_resource_id(self, "JwtSecret"),
            secret_name=f"/ridelist/{env}/jwt",
            description=f"RideList JWT configuration for {env}",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template=(
                    '{"JWT_EXPIRATION":"86400000",'
                    '"JWT_REFRESH_EXPIRATION":"604800000"}'
                ),
                generate_string_key="JWT_SECRET",
                exclude_punctuation=True,
                password_length=64,
            ),
        )

        # =========================================================
        # AWS SECRET
        # =========================================================
        # TEMPORARY APPROACH
        #
        # Kept for EC2 + Docker Compose parity.
        # Later replaced with:
        # - EC2 IAM Role
        # - EKS IRSA
        # =========================================================
        self.aws_secret = secretsmanager.Secret(
            self,
            formulate_resource_id(self, "AwsSecret"),
            secret_name=f"/ridelist/{env}/aws",
            description=f"RideList AWS configuration for {env}",
            secret_object_value={
                "AWS_ACCESS_KEY": secret_value.unsafe_plain_text(""),
                "AWS_SECRET_KEY": secret_value.unsafe_plain_text(""),
                "AWS_REGION": secret_value.unsafe_plain_text(
                    "eu-west-1"
                ),
                "AWS_S3_BUCKET": secret_value.unsafe_plain_text(
                    f"ridelist-media-{env}"
                ),
            },
        )

        # =========================================================
        # SMTP SECRET
        # =========================================================
        # Sensitive SMTP credentials only
        # Mirrors future Kubernetes Secret
        # =========================================================
        self.smtp_secret = secretsmanager.Secret(
            self,
            formulate_resource_id(self, "SmtpSecret"),
            secret_name=f"/ridelist/{env}/smtp",
            description=f"RideList SMTP credentials for {env}",
            secret_object_value={
                "SMTP_USERNAME": secret_value.unsafe_plain_text(""),
                "SMTP_PASSWORD": secret_value.unsafe_plain_text(""),
            },
        )

        # =========================================================
        # APP CONFIG SECRET
        # =========================================================
        # Non-sensitive application config.
        #
        # Intentionally separated from credentials to mirror:
        # - Kubernetes ConfigMaps
        # - Helm values
        #
        # Can later move to:
        # - SSM Parameter Store
        # - ConfigMap
        # =========================================================
        self.app_secret = secretsmanager.Secret(
            self,
            formulate_resource_id(self, "AppConfigSecret"),
            secret_name=f"/ridelist/{env}/app-config",
            description=f"RideList app configuration for {env}",
            secret_object_value={
                # Email
                "EMAIL_SENDER": secret_value.unsafe_plain_text(
                    "mock"
                ),
                "EMAIL_FROM": secret_value.unsafe_plain_text(
                    "noreply@ofspain.click"
                ),
                "EMAIL_FROM_NAME": secret_value.unsafe_plain_text(
                    "RideList"
                ),

                # SMTP Config
                "SMTP_HOST": secret_value.unsafe_plain_text(
                    "smtp.gmail.com"
                ),
                "SMTP_PORT": secret_value.unsafe_plain_text(
                    "587"
                ),

                # Frontend
                "FRONTEND_BASE_URL": secret_value.unsafe_plain_text(
                    "https://ofspain.click"
                ),

                # Image Upload Rules
                "IMAGE_MIN_COUNT": secret_value.unsafe_plain_text(
                    "1"
                ),
                "IMAGE_MAX_COUNT": secret_value.unsafe_plain_text(
                    "10"
                ),
                "IMAGE_MAX_SIZE_MB": secret_value.unsafe_plain_text(
                    "5"
                ),

                # Spring
                "SPRING_PROFILES_ACTIVE":
                    secret_value.unsafe_plain_text(
                        "docker"
                    ),
            },
        )
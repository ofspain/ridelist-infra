import json

from aws_cdk import (
    Stack,
    SecretValue as secret_value,
    aws_secretsmanager as secretsmanager,
    aws_ssm as ssm,
)
from constructs import Construct

from .utils.config_constants import fix_config, Constants
from .utils.utilities import formulate_resource_id


class ConfigurationStack(Stack):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs,
    ):
        super().__init__(
            scope,
            construct_id,
            **kwargs,
        )

        env = self.node.try_get_context(
            Constants.DEPLOYMENT_ENVIRONMENT_KEY
        )
        self.env_config = fix_config(self)


        # =========================================================
        # DATABASE SECRET
        # =========================================================

        self.db_secret = secretsmanager.Secret(
            self,
            formulate_resource_id(
                self,
                "DatabaseSecret",
            ),
            secret_name=f"/ridelist/{env}/database",
            description=(
                f"RideList database credentials "
                f"for {env}"
            ),
            secret_object_value={
                "DB_NAME":
                    secret_value.unsafe_plain_text(""),
                "DB_USERNAME":
                    secret_value.unsafe_plain_text(""),
                "DB_PASSWORD":
                    secret_value.unsafe_plain_text(""),
            },
        )

        # =========================================================
        # JWT SECRET
        # =========================================================

        self.jwt_secret = secretsmanager.Secret(
            self,
            formulate_resource_id(
                self,
                "JwtSecret",
            ),
            secret_name=f"/ridelist/{env}/jwt",
            description=(
                f"RideList JWT configuration "
                f"for {env}"
            ),
            generate_secret_string=(
                secretsmanager.SecretStringGenerator(
                    secret_string_template=json.dumps(
                        {
                            "JWT_EXPIRATION":
                                "86400000",
                            "JWT_REFRESH_EXPIRATION":
                                "604800000",
                        }
                    ),
                    generate_string_key="JWT_SECRET",
                    exclude_punctuation=True,
                    password_length=64,
                )
            ),
        )

        # =========================================================
        # SMTP SECRET
        # =========================================================

        self.smtp_secret = secretsmanager.Secret(
            self,
            formulate_resource_id(
                self,
                "SmtpSecret",
            ),
            secret_name=f"/ridelist/{env}/smtp",
            description=(
                f"RideList SMTP credentials "
                f"for {env}"
            ),
            secret_object_value={
                "SMTP_USERNAME":
                    secret_value.unsafe_plain_text(""),
                "SMTP_PASSWORD":
                    secret_value.unsafe_plain_text(""),
            },
        )

        # =========================================================
        # AWS SECRET
        #
        # Temporary.
        # Eventually replaced entirely by:
        #
        # - EC2 Instance Role
        # - EKS IRSA
        # =========================================================

        self.aws_secret = secretsmanager.Secret(
            self,
            formulate_resource_id(
                self,
                "AwsSecret",
            ),
            secret_name=f"/ridelist/{env}/aws",
            description=(
                f"RideList AWS credentials "
                f"for {env}"
            ),
            secret_object_value={
                "AWS_ACCESS_KEY":
                    secret_value.unsafe_plain_text(""),
                "AWS_SECRET_KEY":
                    secret_value.unsafe_plain_text(""),
            },
        )

        # =========================================================
        # APPLICATION CONFIGURATION
        #
        # Non-sensitive values.
        # Equivalent to future ConfigMap.
        # =========================================================

        self.app_config_parameter = (
            ssm.StringParameter(
                self,
                formulate_resource_id(
                    self,
                    "AppConfigParameter",
                ),
                parameter_name=(
                    f"/ridelist/{env}"
                    "/app-config"
                ),
                string_value=json.dumps(
                    {
                        "EMAIL_SENDER":
                            self.env_config["email_sender"],
                        "EMAIL_FROM":
                            self.env_config["email_from"],
                        "EMAIL_FROM_NAME":
                            "RideList",
                        "SMTP_HOST":
                            self.env_config["smpt_host"],
                        "SMTP_PORT":
                            self.env_config["smpt_port"],
                        "FRONTEND_BASE_URL":
                            self.env_config["frontend_base_url"],
                        "IMAGE_MIN_COUNT":
                            "1",
                        "IMAGE_MAX_COUNT":
                            "10",
                        "IMAGE_MAX_SIZE_MB":
                            "5",
                        "SPRING_PROFILES_ACTIVE":
                            "docker",
                    }
                ),
            )
        )


        # =========================================================
        # DEPLOYMENT IMAGES
        #
        # Updated by GitHub Actions.
        # Not a secret.
        # =========================================================

        self.ecr_images_parameter = (
            ssm.StringParameter(
                self,
                formulate_resource_id(
                    self,
                    "EcrImagesParameter",
                ),
                parameter_name=(
                    f"/ridelist/{env}"
                    "/ecr-images"
                ),
                string_value=json.dumps(
                    {
                        "ECR_FRONTEND_IMAGE": "",
                        "ECR_BACKEND_IMAGE": "",
                    }
                ),
            )
        )
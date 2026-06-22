import json

from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_ecr as ecr,
    RemovalPolicy,
    aws_iam as iam,
    aws_ssm as ssm,
)
from constructs import Construct

from .utils.utilities import (formulate_resource_id, provision_cfnoutput)
from .utils.config_constants import Constants



class StorageStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        env = self.node.try_get_context(Constants.DEPLOYMENT_ENVIRONMENT_KEY)
        is_prod = env == "prod"

        # -----------------------------------
        # S3 BUCKET (MEDIA STORAGE)
        # -----------------------------------
        # -----------------------------------
        # S3 BUCKET (MEDIA STORAGE)
        # -----------------------------------
        self.media_bucket = s3.Bucket(
            self,
            formulate_resource_id(self, "MediaBucket"),
            bucket_name=f"ridelist-media-{env}",

            versioned=is_prod,

            removal_policy=(
                RemovalPolicy.RETAIN
                if env == "prod"
                else RemovalPolicy.DESTROY
            ),

            auto_delete_objects=(env != "prod"),

            # Allow public bucket policies
            block_public_access=s3.BlockPublicAccess(
                block_public_acls=True,
                ignore_public_acls=True,

                # MUST be FALSE for public bucket policy to work
                block_public_policy=False,
                restrict_public_buckets=False,
            ),

            # Recommended modern setting
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
        )

        # Public read access for media files
        self.media_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="PublicReadAccess",
                effect=iam.Effect.ALLOW,
                principals=[iam.AnyPrincipal()],
                actions=["s3:GetObject"],
                resources=[f"{self.media_bucket.bucket_arn}/*"],
            )
        )

        # -----------------------------------
        # ECR REPOSITORIES
        # -----------------------------------

        self.backend_repo = ecr.Repository(
            self,
            formulate_resource_id(self, "BackendRepo"),
            repository_name=f"ridelist-backend-{env}",
            removal_policy=RemovalPolicy.DESTROY if env != "prod" else RemovalPolicy.RETAIN,
            image_scan_on_push=True
        )

        self.frontend_repo = ecr.Repository(
            self,
            formulate_resource_id(self, "FrontendRepo"),
            repository_name=f"ridelist-frontend-{env}",
            removal_policy=RemovalPolicy.DESTROY if env != "prod" else RemovalPolicy.RETAIN,
            image_scan_on_push=True
        )

        provision_cfnoutput(self, "BackendRepoUri", self.backend_repo.repository_uri)
        provision_cfnoutput(self, "FrontendRepoUri", self.frontend_repo.repository_uri)

        # ---------------------------------------------------
        # store s3 metadata in param storage
        # ---------------------------------------------------

        self.aws_s3_bucket = ssm.StringParameter(
            self,
            formulate_resource_id(
                self,
                "AWSS3BUCKETNAME",
            ),
            parameter_name=(
                f"/ridelist/{env}"
                "/s3-bucket-name"
            ),
            string_value=json.dumps({
                "AWS_S3_BUCKET": self.media_bucket.bucket_name
            }),
        )

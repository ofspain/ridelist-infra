from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_ecr as ecr,
    RemovalPolicy,
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
        self.media_bucket = s3.Bucket(
            self,
            formulate_resource_id(self, "MediaBucket"),
            bucket_name=f"ridelist-media-{env}",
            versioned=is_prod,  # only prod gets versioning
            removal_policy=RemovalPolicy.DESTROY if env != "prod" else RemovalPolicy.RETAIN,
            auto_delete_objects=True if env != "prod" else False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL
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

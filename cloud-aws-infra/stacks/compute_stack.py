import json
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_ssm as ssm,
    Size as size,
    RemovalPolicy as removal_policy, Tags, Aws
)
from constructs import Construct

from .utils.utilities import (
    formulate_resource_id,
    provision_cfnoutput,
)
from .utils.config_constants import Constants


class ComputeStack(Stack):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.Vpc,
        ec2_sg: ec2.SecurityGroup,
        **kwargs
    ):
        super().__init__(scope, construct_id, **kwargs)

        self.vpc = vpc
        self.sg = ec2_sg

        env = self.node.try_get_context(
            Constants.DEPLOYMENT_ENVIRONMENT_KEY
        )

        # =========================================================
        # IAM ROLE
        # =========================================================
        self.instance_role = iam.Role(
            self,
            formulate_resource_id(self, "EC2Role"),
            assumed_by=iam.ServicePrincipal(
                "ec2.amazonaws.com"
            ),
            description=(
                f"RideList EC2 instance role "
                f"for {env} environment"
            ),
        )

        # ---------------------------------------------------------
        # SSM SESSION MANAGER
        # Enables browser/CLI shell access
        # Replaces SSH + KeyPairs
        # ---------------------------------------------------------
        self.instance_role.add_managed_policy(
            iam.ManagedPolicy
            .from_aws_managed_policy_name(
                "AmazonSSMManagedInstanceCore"
            )
        )

        # ---------------------------------------------------------
        # ECR PULL ACCESS
        # ---------------------------------------------------------
        self.instance_role.add_managed_policy(
            iam.ManagedPolicy
            .from_aws_managed_policy_name(
                "AmazonEC2ContainerRegistryReadOnly"
            )
        )

        # ---------------------------------------------------------
        # S3 ACCESS
        # ---------------------------------------------------------
        self.instance_role.add_managed_policy(
            iam.ManagedPolicy
            .from_aws_managed_policy_name(
                "AmazonS3FullAccess"
            )
        )

        # ---------------------------------------------------------
        # SECRETS MANAGER ACCESS
        # ---------------------------------------------------------
        self.instance_role.add_managed_policy(
            iam.ManagedPolicy
            .from_aws_managed_policy_name(
                "SecretsManagerReadWrite"
            )
        )

        # ---------------------------------------------------------
        # CLOUDWATCH LOGS
        # ---------------------------------------------------------
        self.instance_role.add_managed_policy(
            iam.ManagedPolicy
            .from_aws_managed_policy_name(
                "CloudWatchAgentServerPolicy"
            )
        )

        # -------------------------------------------------------------
        # Add read access for Parameter Store:
        # -------------------------------------------------------------

        self.instance_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "ssm:GetParameter",
                    "ssm:GetParameters"
                ],
                resources=["*"]
            )
        )

        user_data = ec2.UserData.for_linux()

        user_data.add_commands(

            "dnf update -y || yum update -y",

            "dnf install -y python3 git jq awscli nvme-cli || yum install -y python3 git jq awscli nvme-cli",

            "mkdir -p /opt/ridelist",

            (
                    "echo 'ENVIRONMENT="
                    + env +
                    "' > /opt/ridelist/.env.runtime"
            ),

            "echo READY > /opt/ridelist/bootstrap.status"
        )

        # =========================================================
        # EC2 INSTANCE
        # =========================================================
        self.instance = ec2.Instance(
            self,
            formulate_resource_id(
                self,
                "ComputeInstance"
            ),

            instance_type=ec2.InstanceType(
                "t3.micro"
            ),

            machine_image=(
                ec2.MachineImage
                .latest_amazon_linux2023()
            ),

            vpc=self.vpc,

            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC,
                **(
                    {
                        "availability_zones": [
                            self.vpc.availability_zones[0]
                        ]
                    }
                    if len(self.vpc.availability_zones) == 1
                    else {}
                ),
            ),

            security_group=self.sg,

            role=self.instance_role,

            user_data=user_data,

            # -----------------------------------------------------
            # ROOT VOLUME
            # -----------------------------------------------------
            block_devices=[
                ec2.BlockDevice(
                    device_name="/dev/xvda",

                    volume=ec2.BlockDeviceVolume.ebs(
                        20,

                        volume_type=(
                            ec2.EbsDeviceVolumeType.GP3
                        ),

                        encrypted=True,
                    ),
                )
            ],
        )

        # =========================================================
        # EBS DATA VOLUME
        # =========================================================
        data_volume = ec2.Volume(
            self,
            formulate_resource_id(
                self,
                "DataVolume"
            ),

            availability_zone=(
                self.vpc.availability_zones[0]
            ),

            size=size.gibibytes(20),

            volume_type=(
                ec2.EbsDeviceVolumeType.GP3
            ),

            encrypted=True,

            removal_policy=(
                removal_policy.RETAIN
                if env == "prod"
                else removal_policy.DESTROY
            ),
        )

        data_volume.grant_attach_volume(
            self.instance_role
        )

        ec2.CfnVolumeAttachment(
            self,
            formulate_resource_id(
                self,
                "DataVolumeAttach"
            ),

            volume_id=data_volume.volume_id,

            instance_id=self.instance.instance_id,

            device="/dev/sdh",
        )

        # =========================================================
        # ELASTIC IP
        # =========================================================
        self.eip = ec2.CfnEIP(
            self,
            formulate_resource_id(
                self,
                "ElasticIP"
            ),
        )

        ec2.CfnEIPAssociation(
            self,
            formulate_resource_id(
                self,
                "EIPAssoc"
            ),

            eip=self.eip.ref,

            instance_id=self.instance.instance_id,
        )

        # =========================================================
        # SSM PARAMETER STORE
        # Infrastructure metadata
        # =========================================================
        ssm.StringParameter(
            self,
            formulate_resource_id(
                self,
                "InstanceIdParam"
            ),
            parameter_name=(
                f"/ridelist/{env}"
                "/compute/ec2/instance-id"
            ),
            string_value=json.dumps({
                "EC2_INSTANCE_ID": self.instance.instance_id
            }),
        )

        ssm.StringParameter(
            self,
            formulate_resource_id(
                self,
                "ElasticIPParam"
            ),
            parameter_name=(
                f"/ridelist/{env}"
                "/compute/ec2/elastic-ip"
            ),
            string_value=json.dumps({
                "EC2_ELASTIC_IP": self.eip.ref
            }),
        )

        ssm.StringParameter(
            self,
            formulate_resource_id(
                self,
                "DataVolumeIdParam"
            ),
            parameter_name=(
                f"/ridelist/{env}"
                "/storage/data-volume-id"
            ),
            string_value=json.dumps({
                "DATA_VOLUME_ID": data_volume.volume_id
            }),
        )

        # =========================================================
        # AWS ACCOUNT ID
        # =========================================================

        ssm.StringParameter(
            self,
            formulate_resource_id(
                self,
                "AwsAccountIdParam"
            ),
            parameter_name=(
                f"/ridelist/{env}"
                "/infrastructure/aws-account-id"
            ),
            string_value=json.dumps({
                "AWS_ACCOUNT_ID": Aws.ACCOUNT_ID
            }),
        )

        # =========================================================
        # AWS REGION
        # =========================================================

        ssm.StringParameter(
            self,
            formulate_resource_id(
                self,
                "AwsRegionParam"
            ),
            parameter_name=(
                f"/ridelist/{env}"
                "/infrastructure/aws-region"
            ),
            string_value=json.dumps({
                "AWS_REGION": Aws.REGION
            }),
        )

        # ==========================================================
        # Tagging
        # ==========================================================

        Tags.of(data_volume).add(
            "Application",
            "RideList"
        )

        Tags.of(data_volume).add(
            "Environment",
            env
        )

        Tags.of(data_volume).add(
            "Role",
            "data"
        )

        # =========================================================
        # CFN OUTPUTS
        # =========================================================
        provision_cfnoutput(
            self,
            "InstanceId",
            self.instance.instance_id,
        )

        provision_cfnoutput(
            self,
            "ElasticIP",
            self.eip.ref,
        )

        provision_cfnoutput(
            self,
            "SSMConnectCommand",
            (
                "aws ssm start-session "
                f"--target {self.instance.instance_id}"
            ),
        )
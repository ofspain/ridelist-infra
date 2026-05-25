from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_ssm as ssm,
    Size as size,
    RemovalPolicy as removal_policy,
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

        user_data = ec2.UserData.for_linux()

        user_data.add_commands(

            # =====================================================
            # SYSTEM UPDATE
            # =====================================================
            "yum update -y",

            # =====================================================
            # INSTALL DOCKER
            # =====================================================
            "yum install -y docker",

            "systemctl enable docker",
            "systemctl start docker",

            "usermod -a -G docker ec2-user",

            # =====================================================
            # INSTALL DOCKER COMPOSE V2
            # =====================================================
            "mkdir -p /usr/local/lib/docker/cli-plugins",

            (
                "curl -SL "
                "https://github.com/docker/compose/"
                "releases/latest/download/"
                "docker-compose-linux-x86_64 "
                "-o /usr/local/lib/docker/"
                "cli-plugins/docker-compose"
            ),

            (
                "chmod +x "
                "/usr/local/lib/docker/"
                "cli-plugins/docker-compose"
            ),

            # =====================================================
            # INSTALL UTILITIES
            # =====================================================
            "yum install -y git jq aws-cli certbot",

            # =====================================================
            # LETSENCRYPT + CERTBOT DIRECTORIES
            # =====================================================

            # Create certbot webroot
            "mkdir -p /var/www/certbot",

            # Ensure letsencrypt directory exists
            "mkdir -p /etc/letsencrypt",

            # Permissions
            "chmod 755 /var/www/certbot",
            "chmod 755 /etc/letsencrypt",

            # =====================================================
            # EBS DATA VOLUME SETUP
            # =====================================================

            # Wait for EBS device
            "sleep 10",

            # Detect NVME EBS disk
            "DATA_DEVICE=$(lsblk -ln -o NAME,TYPE | awk '$2==\"disk\" && $1 ~ /nvme1n1/ {print \"/dev/\"$1}')",

            # Fallback
            "if [ -z \"$DATA_DEVICE\" ]; then DATA_DEVICE=/dev/nvme1n1; fi",

            # Format if needed
            "if ! blkid $DATA_DEVICE; then mkfs -t xfs $DATA_DEVICE; fi",

            # Create mount point
            "mkdir -p /data",

            # Mount
            "mount $DATA_DEVICE /data",

            # Persist mount
            "UUID=$(blkid -s UUID -o value $DATA_DEVICE)",

            (
                "grep -q \"$UUID\" /etc/fstab || "
                "echo \"UUID=$UUID /data xfs defaults,nofail 0 2\" >> /etc/fstab"
            ),

            # =====================================================
            # POSTGRES DATA DIRECTORY
            # =====================================================
            "mkdir -p /data/postgres",

            "chmod 777 /data/postgres",

            # =====================================================
            # APPLICATION DIRECTORY
            # =====================================================
            "mkdir -p /opt/ridelist",

            "chown -R ec2-user:ec2-user /opt/ridelist",

            # =====================================================
            # CONFIG LOADER SCRIPT
            # =====================================================

            (
                "cat <<'EOF' > /opt/ridelist/config-loader.sh\n"
                "#!/bin/bash\n"
                "set -euo pipefail\n"
                "\n"
                "ENV=${ENVIRONMENT:-test}\n"
                "BASE_DIR=/opt/ridelist\n"
                "OUT_FILE=$BASE_DIR/.env\n"
                "\n"
                "echo 'Loading config for:' $ENV\n"
                "> $OUT_FILE\n"
                "\n"
                "SECRETS=(database jwt app-config smtp aws)\n"
                "\n"
                "for SECRET in \"${SECRETS[@]}\"; do\n"
                "  echo \"Fetching $SECRET\"\n"
                "  VALUE=$(aws secretsmanager get-secret-value \\\n"
                "    --secret-id /ridelist/$ENV/$SECRET \\\n"
                "    --query SecretString --output text)\n"
                "\n"
                "  echo \"$VALUE\" | jq -r 'to_entries[] | \"\\(.key)=\\(.value)\"' >> $OUT_FILE\n"
                "done\n"
                "\n"
                "chmod 600 $OUT_FILE\n"
                "echo 'DONE'\n"
                "EOF\n"
            ),

            "chmod +x /opt/ridelist/config-loader.sh",

            "chown ec2-user:ec2-user /opt/ridelist/config-loader.sh",

            # =====================================================
            # ENVIRONMENT FILE
            # =====================================================

            (
                    "echo 'ENVIRONMENT=" +
                    self.node.try_get_context(Constants.DEPLOYMENT_ENVIRONMENT_KEY) +
                    "' > /opt/ridelist/.env.runtime"
            ),

            "chown ec2-user:ec2-user /opt/ridelist/.env.runtime",

            # =====================================================
            # LOAD ENV CONFIG
            # =====================================================
            "/opt/ridelist/config-loader.sh",

            # =====================================================
            # COMPLETE MARKER
            # =====================================================
            "echo 'RIDELIST_SETUP_COMPLETE' > /opt/ridelist/.setup_complete",

            "echo 'User data script completed'",
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
                f"/compute/ec2/instance-id"
            ),

            string_value=self.instance.instance_id,
        )

        ssm.StringParameter(
            self,
            formulate_resource_id(
                self,
                "ElasticIPParam"
            ),

            parameter_name=(
                f"/ridelist/{env}"
                f"/compute/ec2/elastic-ip"
            ),

            string_value=self.eip.ref,
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
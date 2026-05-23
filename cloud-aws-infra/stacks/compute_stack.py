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

        env = self.node.try_get_context(Constants.DEPLOYMENT_ENVIRONMENT_KEY)

        # ----------------------------
        # IAM ROLE
        # ----------------------------
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

        # SSM Session Manager
        # (SSH alternative — more secure)
        self.instance_role.add_managed_policy(
            iam.ManagedPolicy
            .from_aws_managed_policy_name(
                "AmazonSSMManagedInstanceCore"
            )
        )

        # ECR pull
        self.instance_role.add_managed_policy(
            iam.ManagedPolicy
            .from_aws_managed_policy_name(
                "AmazonEC2ContainerRegistryReadOnly"
            )
        )

        # S3 media bucket access
        self.instance_role.add_managed_policy(
            iam.ManagedPolicy
            .from_aws_managed_policy_name(
                "AmazonS3FullAccess"
            )
        )

        # Secrets Manager read
        # (for production secret injection)
        self.instance_role.add_managed_policy(
            iam.ManagedPolicy
            .from_aws_managed_policy_name(
                "SecretsManagerReadWrite"
            )
        )

        # CloudWatch logs
        self.instance_role.add_managed_policy(
            iam.ManagedPolicy
            .from_aws_managed_policy_name(
                "CloudWatchAgentServerPolicy"
            )
        )

        # ----------------------------
        # USER DATA
        # Runs once on first boot
        # Sets up Docker + Compose
        # Mounts EBS data volume
        # ----------------------------
        user_data = ec2.UserData.for_linux()
        user_data.add_commands(
            # System update
            "yum update -y",

            # Install Docker
            "yum install -y docker",
            "systemctl enable docker",
            "systemctl start docker",
            # Add ec2-user to docker group
            # (so ec2-user can run docker
            # without sudo)
            "usermod -a -G docker ec2-user",

            # Install Docker Compose plugin
            # (modern v2 style: docker compose)
            "mkdir -p /usr/local/lib/docker/cli-plugins",
            (
                "curl -SL https://github.com/"
                "docker/compose/releases/latest/"
                "download/docker-compose-linux-"
                "x86_64 "
                "-o /usr/local/lib/docker/"
                "cli-plugins/docker-compose"
            ),
            (
                "chmod +x /usr/local/lib/docker/"
                "cli-plugins/docker-compose"
            ),

            # Install useful tools
            "yum install -y git jq aws-cli",

            # ----------------------------
            # EBS DATA VOLUME SETUP
            # The 20GB volume is attached
            # as /dev/sdh (or /dev/xvdh
            # on newer kernels)
            # We format and mount it to
            # /data for postgres data
            # ----------------------------

            # Wait for volume to appear
            "sleep 10",

            # Check if volume needs formatting
            # (only format on first boot)
            (
                "if ! blkid /dev/xvdh; then "
                "mkfs -t xfs /dev/xvdh; "
                "fi"
            ),

            # Create mount point
            "mkdir -p /data/postgres",

            # Mount the volume
            "mount /dev/xvdh /data",

            # Make mount persistent across reboots
            # Add to /etc/fstab
            (
                "echo '/dev/xvdh /data xfs "
                "defaults,nofail 0 2' "
                ">> /etc/fstab"
            ),

            # Create postgres data directory
            # with correct permissions
            "mkdir -p /data/postgres",
            "chmod 777 /data/postgres",

            # Create app directory structure
            "mkdir -p /opt/ridelist",
            "chown ec2-user:ec2-user "
            "/opt/ridelist",

            # ----------------------------
            # SIGNAL THAT SETUP IS DONE
            # Write a marker file so we
            # can check setup completed
            # ----------------------------
            "echo 'RIDELIST_SETUP_COMPLETE' "
            "> /opt/ridelist/.setup_complete",

            "echo 'User data script completed'",
        )

        # ----------------------------
        # KEY PAIR FOR SSH ACCESS
        # Creates a key pair in AWS
        # Download the private key from
        # AWS Console → EC2 → Key Pairs
        # ----------------------------
        key_pair = ec2.KeyPair(
            self,
            formulate_resource_id(self, "KeyPair"),
            key_pair_name=f"ridelist-{env}-key",
        )

        # ----------------------------
        # EC2 INSTANCE
        # ----------------------------
        self.instance = ec2.Instance(
            self,
            formulate_resource_id(
                self, "ComputeInstance"
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
                    {"availability_zones": [self.vpc.availability_zones[0]]}
                    if len(self.vpc.availability_zones) == 1
                    else {}
                ),
            ),
            security_group=self.sg,
            role=self.instance_role,
            user_data=user_data,
            key_pair=key_pair,
            # Encrypt the root volume
            block_devices=[
                ec2.BlockDevice(
                    device_name="/dev/xvda",
                    volume=ec2.BlockDeviceVolume
                    .ebs(
                        20,
                        volume_type=(
                            ec2.EbsDeviceVolumeType
                            .GP3
                        ),
                        encrypted=True,
                    ),
                )
            ],
        )

        # ----------------------------
        # EBS DATA VOLUME
        # Separate from root volume
        # Postgres data lives here
        # Survives instance replacement
        # ----------------------------
        data_volume = ec2.Volume(
            self,
            formulate_resource_id(
                self, "DataVolume"
            ),
            availability_zone=self.vpc.availability_zones[0],
            size=size.gibibytes(20),
            volume_type=(
                ec2.EbsDeviceVolumeType.GP3
            ),
            encrypted=True,
            removal_policy=(
                # Keep data volume even if
                # stack is destroyed
                # Change to DESTROY for
                # disposable test envs
                removal_policy.RETAIN
                if env == "prod"
                else removal_policy.DESTROY
            ),
        )

        data_volume.grant_attach_volume(
            self.instance_role
            #,[self.instance]
        )

        ec2.CfnVolumeAttachment(
            self,
            formulate_resource_id(
                self, "DataVolumeAttach"
            ),
            volume_id=data_volume.volume_id,
            instance_id=self.instance.instance_id,
            device="/dev/sdh",
        )

        # ----------------------------
        # ELASTIC IP
        # Static public IP
        # Survives instance stop/start
        # Point your DNS here
        # ----------------------------
        self.eip = ec2.CfnEIP(
            self,
            formulate_resource_id(
                self, "ElasticIP"
            ),
            # Keep EIP even after destroy
            # Prevents DNS breaking
            # if stack is recreated
        )

        ec2.CfnEIPAssociation(
            self,
            formulate_resource_id(
                self, "EIPAssoc"
            ),
            eip=self.eip.ref,
            instance_id=self.instance.instance_id,
        )

        # ----------------------------
        # SSM PARAMETER STORE
        # Store instance details for
        # CI/CD and Ansible to use
        # ----------------------------
        ssm.StringParameter(
            self,
            formulate_resource_id(
                self, "InstanceIdParam"
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
                self, "ElasticIPParam"
            ),
            parameter_name=(
                f"/ridelist/{env}"
                f"/compute/ec2/elastic-ip"
            ),
            string_value=self.eip.ref,
        )

        ssm.StringParameter(
            self,
            formulate_resource_id(self, "KeyPairPrivateKeyParam"),
            parameter_name=(
                f"/ridelist/{env}"
                f"/compute/ec2/keypair-secret-arn"
            ),
            string_value=(
                f"arn:aws:secretsmanager:{self.region}"
                f":{self.account}:secret:/ec2/keypair/"
                f"{key_pair.key_pair_id}"
            ),
        )

        # ----------------------------
        # CFN OUTPUTS
        # Shown after cdk deploy
        # ----------------------------
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
            "KeyPairName",
            key_pair.key_pair_name,
        )

        provision_cfnoutput(
            self,
            "SSHCommand",
            f"ssh -i ridelist-{env}-key.pem "
            f"ec2-user@{self.eip.ref}",
        )
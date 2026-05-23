from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ssm as ssm,
)
from constructs import Construct

from .utils.utilities import (
    formulate_resource_id,
    provision_cfnoutput
)

from .utils.config_constants import fix_az_config, Constants


class VPCStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.env_name = self.node.try_get_context(Constants.DEPLOYMENT_ENVIRONMENT_KEY)

        vpc_name = formulate_resource_id(self, "VPC")
        self.env_config = fix_az_config(self)

        # ----------------------------
        # NETWORK STRATEGY BY ENV
        # ----------------------------

        is_prod = self.env_name == "prod"

        self.max_azs = self.env_config["max_az"]

        # TEST/STAGING = NO NAT
        nat_gateways = 1 if is_prod else 0

        # PRIVATE SUBNETS ONLY IN PROD
        subnet_config = [
            ec2.SubnetConfiguration(
                cidr_mask=24,
                name="PublicSubnet",
                subnet_type=ec2.SubnetType.PUBLIC,
            )
        ]

        if is_prod:
            subnet_config.append(
                ec2.SubnetConfiguration(
                    cidr_mask=24,
                    name="PrivateSubnet",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                )
            )

        # ----------------------------
        # VPC
        # ----------------------------
        self.vpc = ec2.Vpc(
            self,
            vpc_name,
            max_azs=self.max_azs,
            nat_gateways=nat_gateways,
            subnet_configuration=subnet_config
        )

        # ----------------------------
        # SSM PARAMETER STORE
        # ----------------------------
        self.vpc_id_store = ssm.StringParameter(
            self,
            formulate_resource_id(self, "VpcIdParam"),
            parameter_name=f"/ridelist/{self.env_name}/network/vpc/id",
            string_value=self.vpc.vpc_id
        )

        # Store subnet IDs (useful later for Ansible / ECS / automation)
        if self.vpc.public_subnets:
            ssm.StringParameter(
                self,
                formulate_resource_id(self, "PublicSubnetParam"),
                parameter_name=f"/ridelist/{self.env_name}/network/subnet/public/id",
                string_value=self.vpc.public_subnets[0].subnet_id
            )

        if is_prod and self.vpc.private_subnets:
            ssm.StringParameter(
                self,
                formulate_resource_id(self, "PrivateSubnetParam"),
                parameter_name=f"/ridelist/{self.env_name}/network/subnet/private/id",
                string_value=self.vpc.private_subnets[0].subnet_id
            )

        # ----------------------------
        # SECURITY GROUPS
        # ----------------------------
        self.ec2_sg = self._provision_ec2_sg()

        # ----------------------------
        # OUTPUTS
        # ----------------------------
        provision_cfnoutput(self, "VPCID", self.vpc.vpc_id)

        provision_cfnoutput(
            self,
            "PUBLICSUBNETID",
            self.vpc.public_subnets[0].subnet_id
        )

        if is_prod:
            provision_cfnoutput(
                self,
                "PRIVATESUBNETID",
                self.vpc.private_subnets[0].subnet_id
            )

    # ----------------------------
    # SECURITY GROUP
    # ----------------------------
    def _provision_ec2_sg(self):

        sg_name = formulate_resource_id(self, "EC2SG")

        sg = ec2.SecurityGroup(
            self,
            sg_name,
            vpc=self.vpc,
            allow_all_outbound=True,
            description="RideList EC2 security group"
        )

        # SSH ONLY FOR NON-PROD (temporary dev convenience)
        if self.env_name != "prod":
            sg.add_ingress_rule(
                ec2.Peer.any_ipv4(),
                ec2.Port.tcp(22),
                "allow ssh (dev only)"
            )

        sg.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(80),
            "allow http"
        )

        sg.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(443),
            "allow https"
        )

        return sg
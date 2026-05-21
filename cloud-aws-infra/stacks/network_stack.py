from aws_cdk import (
    Stack,
    aws_ec2 as ec2, CfnOutput,
    aws_ssm as ssm,
)
from constructs import Construct

class VPCStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        vpc_name = formulate_resource_id(self, "VPC")
        az_config = load_configuration(self, 'az')
        self.vpc = ec2.Vpc(
            self, vpc_name, max_azs=az_config['max_az_number'],
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    cidr_mask=24,
                    name="PublicSubnet",
                    subnet_type=ec2.SubnetType.PUBLIC,
                ),
                ec2.SubnetConfiguration(
                    cidr_mask=24,
                    name="PrivateSubnet",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                )
            ]
        )
        store_name = formulate_resource_id(self, "StringParameter")

        self.vpc_id_store = ssm.StringParameter(self, store_name, parameter_name="vpcstack_vpc_vpc_id",
                                 string_value=self.vpc.vpc_id)

        self.ec2_sg = None
        self.provision_ec2_sg()

        provision_cfnoutput(self, "VPCID", self.vpc.vpc_id)
        provision_cfnoutput(self, "PUBLICSUBNETID", self.vpc.public_subnets[0].subnet_id)
        provision_cfnoutput(self, "PRIVATESUBNETID", self.vpc.private_subnets[0].subnet_id)

    def provision_ec2_sg(self):
        sg_name = formulate_resource_id(self, "SecurityGroup")
        self.ec2_sg = ec2.SecurityGroup(
            self, sg_name, vpc=self.vpc,
            allow_all_outbound=True
        )

        self.ec2_sg.add_ingress_rule(
            ec2.Peer.any_ipv4(), ec2.Port.tcp(22), "allow ssh"
        )
        self.ec2_sg.add_ingress_rule(
            ec2.Peer.any_ipv4(), ec2.Port.tcp(80), "allow http"
        )
        self.ec2_sg.add_ingress_rule(
            ec2.Peer.any_ipv4(), ec2.Port.tcp(443), "allow https"  # Corrected port
        )

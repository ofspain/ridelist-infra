#!/usr/bin/env python3
import aws_cdk as cdk

from stacks.network_stack import VPCStack
from stacks.storage_stack import StorageStack
from stacks.compute_stack import ComputeStack
from stacks.config_stack import ConfigurationStack
from stacks.utils.config_constants import Constants

app = cdk.App()

# Read environment from context
# Deploy with:
# cdk deploy --all -c environment=test
# cdk deploy --all -c environment=prod
env_name = app.node.try_get_context(Constants.DEPLOYMENT_ENVIRONMENT_KEY)

if not env_name:
    raise ValueError(
        "environment context is required.\n"
        "Run: cdk deploy --all "
        "-c environment=test"
    )

aws_env = cdk.Environment(
    account=app.node.try_get_context("account"),
    region=app.node.try_get_context(
        "region"
    ) or "eu-west-1",
)

# ----------------------------
# STACK INSTANTIATION ORDER
# Each stack can reference the
# previous stack's outputs
# ----------------------------

# 1. Network first
vpc_stack = VPCStack(
    app,
    f"RideList-{env_name}-VPC",
    env=aws_env,
)

# 2. Storage (independent of VPC)
storage_stack = StorageStack(
    app,
    f"RideList-{env_name}-Storage",
    env=aws_env,
)

# 3. Secrets (independent of VPC)
config_stack = ConfigurationStack(
    app,
    f"RideList-{env_name}-Configs",
    env=aws_env,
)

# 4. Compute (depends on VPC)
compute_stack = ComputeStack(
    app,
    f"RideList-{env_name}-Compute",
    vpc=vpc_stack.vpc,
    ec2_sg=vpc_stack.ec2_sg,
    env=aws_env,
)

# Explicit dependency
compute_stack.add_dependency(vpc_stack)

app.synth()
import json
from typing import Dict, Any

from aws_cdk import Stack, CfnOutput
from constructs import Construct



def formulate_resource_id(parent: Stack, resource_type: str)->str:
    env = parent.node.try_get_context(Constants.DEPLOYMENT_ENVIRONMENT_KEY)
    resource_id = parent.node.id

    return f"{resource_type}-{resource_id}-{env}".lower()

def load_configuration(parent: Construct, entity: str) -> Dict[str, Any]:
    """Load configuration based on environment"""
    env = parent.node.try_get_context(Constants.DEPLOYMENT_ENVIRONMENT_KEY)
    if not env:
        raise ValueError("Deployment environment is not set in context")

    # Use __file__ to resolve from this file's location
    resolver = PathResolver(__file__)

    config_path = resolver.path_from_root("cdk_app_project","config", f"{entity}_config.json")

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r") as f:
        loaded_config = json.load(f)

    if env not in loaded_config:
        raise KeyError(f"Configuration for environment '{env}' not found in {config_path.name}")

    return loaded_config[env]


def provision_cfnoutput(parent: Stack, name: str, value: str):
    CfnOutput(parent, formulate_resource_id(parent, f"CfnOutput_{name}"), value=value)


from aws_cdk import aws_ec2 as ec2


def get_enum_value(enum_class, value_str: str, default=None):
    """
    Safely resolve a value from an enum class using a string.

    Args:
        enum_class: The enum class to search (e.g., ec2.InstanceSize).
        value_str: The string name of the enum member (e.g., 'MEDIUM').
        default: The fallback value if `value_str` is not found.

    Returns:
        The resolved enum value or the default.

    Raises:
        ValueError if value_str is invalid and no default is provided.
    """
    try:
        return getattr(enum_class, value_str.upper())
    except AttributeError:
        if default is not None:
            return default
        raise ValueError(f"{value_str!r} is not a valid member of {enum_class.__name__}")



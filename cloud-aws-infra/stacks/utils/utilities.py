import json
from typing import Dict, Any

from aws_cdk import Stack, CfnOutput
from constructs import Construct
from .config_constants import Constants



def formulate_resource_id(parent: Stack, resource_type: str)->str:
    env = parent.node.try_get_context(Constants.DEPLOYMENT_ENVIRONMENT_KEY)
    resource_id = parent.node.id

    return f"{resource_type}-{resource_id}-{env}".lower()


def provision_cfnoutput(parent: Stack, name: str, value: str):
    CfnOutput(parent, formulate_resource_id(parent, f"CfnOutput_{name}"), value=value)


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



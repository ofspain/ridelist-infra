from aws_cdk import Stack


def fix_az_config(parent: Stack):
    env = parent.node.try_get_context(Constants.DEPLOYMENT_ENVIRONMENT_KEY)
    configs = {
        "test": {
            "max_az": 1
        },
        "staging": {
            "max_az": 1
        },
        "prod": {
            "max_az": 2
        }
    }

    return configs.get(env)


class Constants:
    DEPLOYMENT_ENVIRONMENT_KEY = "environment"

    def __init__(self):
        pass


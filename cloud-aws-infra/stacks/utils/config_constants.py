from aws_cdk import Stack


def fix_config(parent: Stack):
    env = parent.node.try_get_context(Constants.DEPLOYMENT_ENVIRONMENT_KEY)
    configs = {
        "test": {
            "max_az": 1,
            "email_from":"noreply@ofspain.click",
            "email_sender": "mock",
            "smpt_host":"smtp.gmail.com",
            "smpt_port":"587",
            "frontend_base_url":"https://ofspain.click"
        },
        "staging": {
            "max_az": 1,
            "email_from": "noreply@ofspain.click",
            "email_sender":"mock",
            "smpt_host": "smtp.gmail.com",
            "smpt_port": "587",
            "frontend_base_url": "https://ofspain.click"
        },
        "prod": {
            "max_az": 2,
            "email_from": "noreply@ridelist.ng",
            "email_sender": "aws",
            "smpt_host": "smtp.gmail.com",
            "smpt_port": "587",
            "frontend_base_url": "https://ridelist.ng"
        }
    }

    return configs.get(env)


class Constants:
    DEPLOYMENT_ENVIRONMENT_KEY = "environment"

    def __init__(self):
        pass


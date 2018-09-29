from models import Config, ExAServer


def get_config() -> Config:
    """Config instance"""
    f'{Config}'
    return Config.query.one()


def get_server() -> ExAServer:
    """Server instance """
    return ExAServer.query.one()

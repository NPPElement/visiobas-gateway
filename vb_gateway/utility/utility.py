import os
from logging import getLogger, Formatter, Logger
from logging.handlers import RotatingFileHandler
from pathlib import Path


def read_cfg_from_env() -> dict:
    """
    :return: Config, read from environment variables
    """
    try:
        config = {
            'http': {
                'get_host': os.environ['HTTP_GET_HOST'],
                # 'post_hosts': os.environ['HTTP_POST_HOSTS'].split(), # todo
                'port': int(os.environ.get('HTTP_PORT', 8080)),
                'auth': {
                    'login': os.environ['HTTP_AUTH_LOGIN'],
                    'password': os.environ['HTTP_AUTH_PASSWORD']
                }
            },
            'bacnet_verifier': {
                'http_enable': True if os.environ.get(
                    'HTTP_ENABLE').lower() == 'true' else False,
                'mqtt_enable': True if os.environ.get(
                    'MQTT_ENABLE').lower() == 'true' else False,
            },
            'bacnet': {
                'default_update_period': int(
                    os.environ.get('BACNET_DEFAULT_UPDATE_PERIOD', 10)),
                'interfaces': os.environ.get('BACNET_INTERFACES', '').split()
            },
            'modbus': {
                'default_update_period': int(
                    os.environ.get('MODBUS_DEFAULT_UPDATE_PERIOD', 10))
            }
        }
    except KeyError:
        raise ValueError(
            "Please ensure environment variables are set to: \n"
            "'HTTP_GET_HOST'\n'HTTP_POST_HOSTS'\n"
            "'HTTP_AUTH_LOGIN'\n'HTTP_AUTH_PASSWORD'\n\n"
            "Also you can provide optional variables: \n"
            "'HTTP_PORT' by default = 8080\n"
            "'HTTP_ENABLE' by default = FALSE\n"
            "'MQTT_ENABLE' by default = FALSE\n"
            "'BACNET_DEFAULT_UPDATE_PERIOD' by default = 10\n"
            "'MODBUS_DEFAULT_UPDATE_PERIOD' by default = 10\n"
        )
    else:
        return config


def get_file_logger(logger_name: str, file_size_bytes: int,
                    file_path: Path, log_format: str = None) -> Logger:
    log_level = os.environ.get('FILE_LOG_LEVEL', 'INFO')

    if log_format is None:
        log_format = ('%(levelname)-8s [%(asctime)s] [%(threadName)s] %(name)s - '
                      '(%(filename)s).%(funcName)s(%(lineno)d): %(message)s')

    logger = getLogger(logger_name)
    logger.setLevel(level=log_level)
    logger.handlers = []  # Remove all handlers

    file_handler = RotatingFileHandler(filename=file_path,
                                       mode='a',
                                       maxBytes=file_size_bytes,
                                       backupCount=1,
                                       encoding='utf-8')
    formatter = Formatter(log_format)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

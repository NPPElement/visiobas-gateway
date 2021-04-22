import os
from logging import getLogger, Formatter, Logger, CRITICAL
from logging.handlers import RotatingFileHandler
from os import environ
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_FORMAT = os.environ.get('LOG_FORMAT',
                            '%(levelname)-8s [%(asctime)s] %(name)s'
                            '.%(funcName)s(%(lineno)d): %(message)s'
                            )
_MEGABYTE = 1024 ** 2
LOG_MB_COUNT = os.environ.get('LOG_FILE_SIZE', 50)
LOG_FILE_SIZE = LOG_MB_COUNT * _MEGABYTE


def get_file_logger(logger_name: str, size_bytes: int = LOG_FILE_SIZE,
                    log_format: str = LOG_FORMAT) -> Logger:
    log_level = environ.get('FILE_LOG_LEVEL', 'DEBUG')

    # if log_format is None:
    #     log_format = LOG_FORMAT

    logger = getLogger(logger_name)
    logger.setLevel(level=log_level)
    logger.handlers = []  # Remove all handlers

    _log_file_path = BASE_DIR / f'logs/{logger_name}.log'
    file_handler = RotatingFileHandler(filename=_log_file_path,
                                       mode='a',
                                       maxBytes=size_bytes,
                                       backupCount=1,
                                       encoding='utf-8',
                                       )
    formatter = Formatter(log_format)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def disable_loggers(loggers: tuple[str, ...]) -> None:
    """Disables loggers."""

    for logger in loggers:
        logger = getLogger(logger)
        logger.setLevel(level=CRITICAL)
        logger.handlers = []

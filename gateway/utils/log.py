import os
from logging import getLogger, Formatter, Logger
from logging.handlers import RotatingFileHandler
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_FORMAT = os.getenv('GW_LOG_FORMAT',
                       '%(levelname)-8s [%(asctime)s] %(name)s'
                       '.%(funcName)s(%(lineno)d): %(message)s')
_MEGABYTE = 1024 ** 2
LOG_MB_COUNT = int(os.getenv('GW_LOG_FILE_SIZE', 50))
LOG_FILE_SIZE = LOG_MB_COUNT * _MEGABYTE


def get_file_logger(name: str, size_bytes: int = LOG_FILE_SIZE,
                    log_format: str = LOG_FORMAT) -> Logger:
    log_level = os.getenv('GW_LOG_FILE_LEVEL', 'DEBUG')

    # if log_format is None:
    #     log_format = LOG_FORMAT

    logger = getLogger(name)
    logger.setLevel(level=log_level)
    logger.handlers = []  # Remove all handlers

    _log_file_path = BASE_DIR / f'logs/{name}.log'
    file_handler = RotatingFileHandler(filename=_log_file_path,
                                       mode='a',
                                       maxBytes=size_bytes,
                                       backupCount=1,
                                       encoding='utf-8', )
    formatter = Formatter(log_format)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


# def disable_loggers(loggers: tuple[str, ...]) -> None:
#     """Disables loggers."""
#
#     for logger in loggers:
#         logger = getLogger(logger)
#         logger.setLevel(level=CRITICAL)
#         logger.handlers = []

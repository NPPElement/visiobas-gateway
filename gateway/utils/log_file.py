import os
from logging import getLogger, Logger
from logging.handlers import RotatingFileHandler
from typing import Optional, Union, Any

from .log_extra_formatter import ExtraFormatter
from gateway import BASE_DIR

_MEGABYTE = 1024 ** 2


# LOG_FORMAT = os.getenv('GW_LOG_FORMAT',
#                        '%(levelname)-8s [%(asctime)s] %(name)s'
#                        '.%(funcName)s(%(lineno)d): %(message)s')

# LOG_MB_COUNT = int(os.getenv('GW_LOG_FILE_SIZE', 50))
# LOG_FILE_SIZE = LOG_MB_COUNT * _MEGABYTE


def get_file_logger(name: str,
                    filename: Optional[Any] = None,
                    level: Optional[Union[int, str]] = None,
                    log_size_bytes: Optional[int] = None,
                    # log_format: Optional[str] = None
                    ) -> Logger:
    """Returns Logger with RotatingFileHandler.

    If params is not specified they gets from environment, before default.

    Args:
        name: name of logger (module). Should provide __name__.
        filename:
        level: logging level.
            Default: DEBUG
        log_size_bytes: Size of file in MB.
            Default: 50 MB
        # log_format: Using format of logs

    Returns:
        Logger with RotatingFileHandler.
    """

    log_level = level or os.getenv('GW_LOG_FILE_LEVEL', 'DEBUG')
    log_filename = filename or BASE_DIR / f'logs/{name}.log'
    log_size_bytes = log_size_bytes or int(os.getenv('GW_LOG_FILE_SIZE', 50)) * _MEGABYTE

    # if log_format is None:
    #     log_format = os.getenv('GW_LOG_FORMAT',
    #                            '%(levelname)-8s [%(asctime)s] %(name)s'
    #                            '.%(funcName)s(%(lineno)d): %(message)s')

    logger = getLogger(name)
    logger.setLevel(level=log_level)
    # logger.handlers = []  # Remove all handlers

    file_handler = RotatingFileHandler(filename=log_filename,
                                       mode='a',
                                       maxBytes=log_size_bytes,
                                       backupCount=1,
                                       encoding='utf-8', )
    # formatter = ExtraFormatter(log_format)
    # file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

# def disable_loggers(loggers: tuple[str, ...]) -> None:
#     """Disables loggers."""
#
#     for logger in loggers:
#         logger = getLogger(logger)
#         logger.setLevel(level=CRITICAL)
#         logger.handlers = []

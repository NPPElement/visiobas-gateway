import os
from logging import getLogger, Logger
from logging.handlers import RotatingFileHandler
from typing import Optional, Union, Any

from gateway import BASE_DIR
from .log_extra_formatter import ExtraFormatter

_MEGABYTE = 10 ** 6


def get_file_logger(name: str,
                    filename: Optional[Any] = None,
                    level: Optional[Union[int, str]] = None,
                    size_mb: Optional[int] = None,
                    fmt: Optional[str] = None
                    ) -> Logger:
    """Returns Logger with RotatingFileHandler.

    If params is not specified they gets from environment, before default.

    Args:
        name: name of logger (module). Should provide `__name__`.
        filename:
        level: logging level.
            Default: DEBUG
        size_mb: Size of file in MB.
            Default: 50 MB
        fmt: Using format of logs

    Returns:
        Logger with RotatingFileHandler.
    """

    log_level = level or os.getenv('GTW_LOG_FILE_LEVEL', 'DEBUG')
    log_filename = filename or BASE_DIR / f'logs/{name}.log'
    size_mb = (size_mb or int(os.getenv('GTW_LOG_FILE_SIZE', 50))) * _MEGABYTE
    fmt = fmt or os.getenv('GTW_LOG_FORMAT', 
                           '%(levelname)-8s [%(asctime)s] %(name)s.%(funcName)s(%(lineno)d): %(message)s')
    logger = getLogger(name)
    logger.setLevel(level=log_level)
    # logger.handlers = []  # Remove all handlers

    if not logger.hasHandlers():
        file_handler = RotatingFileHandler(filename=log_filename, mode='a', maxBytes=size_mb,
                                           backupCount=1, encoding='utf-8', )
        formatter = ExtraFormatter(fmt=fmt)
        file_handler.setFormatter(fmt=formatter)
        logger.addHandler(file_handler)

    return logger

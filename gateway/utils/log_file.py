from logging import Logger, getLogger
from logging.handlers import RotatingFileHandler

from ..models import LogSettings
from .log_extra_formatter import ExtraFormatter

_MEGABYTE = 10 ** 6


def get_file_logger(name: str, settings: LogSettings = LogSettings()) -> Logger:  # fixme
    """Gets Logger with RotatingFileHandler.

    Args:
        name: name of logger (module). Should provide `__name__`.
        settings:

    Returns:
        Logger with RotatingFileHandler.
    """
    logger = getLogger(name)
    logger.setLevel(level=settings.file_level)
    logger.handlers = []  # Remove all handlers

    filename = settings.logs_path / f"{name}.log"
    size = settings.file_size + _MEGABYTE

    file_handler = RotatingFileHandler(
        filename=filename,
        mode="a",
        maxBytes=size,
        backupCount=1,
        encoding="utf-8",
    )
    formatter = ExtraFormatter(fmt=settings.format)
    file_handler.setFormatter(fmt=formatter)
    logger.addHandler(file_handler)

    return logger

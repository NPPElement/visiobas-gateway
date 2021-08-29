from logging import CRITICAL, Formatter, Logger, getLogger
from logging.handlers import RotatingFileHandler
from os import environ
from pathlib import Path


def get_file_logger(
    logger_name: str, size_bytes: int, file_path: Path, log_format: str = None
) -> Logger:
    log_level = environ.get("FILE_LOG_LEVEL", "DEBUG")

    if log_format is None:
        log_format = (
            "%(levelname)-8s [%(asctime)s] [%(threadName)s] %(name)s - "
            "(%(filename)s).%(funcName)s(%(lineno)d): %(message)s"
        )

    logger = getLogger(logger_name)
    logger.setLevel(level=log_level)
    logger.handlers = []  # Remove all handlers

    file_handler = RotatingFileHandler(
        filename=file_path,
        mode="a",
        maxBytes=size_bytes,
        backupCount=1,
        encoding="utf-8",
    )
    formatter = Formatter(log_format)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def disable_loggers(loggers: tuple[str, ...]) -> None:
    """Disable unused loggers"""

    for logger in loggers:
        logger = getLogger(logger)
        logger.setLevel(level=CRITICAL)
        logger.handlers = []

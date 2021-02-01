from logging import getLogger, Formatter, Logger, CRITICAL
from logging.handlers import RotatingFileHandler
from os import environ
from pathlib import Path

_base_path = Path(__file__).resolve().parent.parent
_log_fmt = ('%(levelname)-8s [%(asctime)s] [%(threadName)s] %(name)s'
            '.%(funcName)s(%(lineno)d): %(message)s'
            )


def get_file_logger(logger_name: str, size_bytes: int,
                    log_format: str = None) -> Logger:
    log_level = environ.get('FILE_LOG_LEVEL', 'DEBUG')

    if log_format is None:
        log_format = _log_fmt

    logger = getLogger(logger_name)
    logger.setLevel(level=log_level)
    logger.handlers = []  # Remove all handlers

    _log_file_path = _base_path / f'logs/{logger_name}.log'
    file_handler = RotatingFileHandler(filename=_log_file_path,
                                       mode='a',
                                       maxBytes=size_bytes,
                                       backupCount=1,
                                       encoding='utf-8'
                                       )
    formatter = Formatter(log_format)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def disable_loggers(loggers: tuple[str, ...]) -> None:
    """ Disable unused loggers """

    for logger in loggers:
        logger = getLogger(logger)
        logger.setLevel(level=CRITICAL)
        logger.handlers = []

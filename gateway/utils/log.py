import logging
from functools import wraps
from logging.handlers import RotatingFileHandler
from typing import Any, Callable

from ..models.settings.log_settings import LogSettings

_MEGABYTE = 10 ** 6


class ExtraFormatter(logging.Formatter):
    """Formatter for display `extra` params.

    Adopted from:
        <https://stackoverflow.com/questions/56559971/show-extra-fields-when
    -logging-to-console-in-python>
    """

    # Keys in `extra` must not have reserved names
    reserved_keys = {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
        "asctime",
    }

    def format(self, record: logging.LogRecord) -> str:
        string = super().format(record)
        extra = {k: v for k, v in record.__dict__.items() if k not in self.reserved_keys}
        if len(extra) > 0:
            string += " >>> " + str(extra)
        return string


def get_file_logger(name: str, settings: LogSettings) -> logging.Logger:
    """Gets Logger with RotatingFileHandler.

    Args:
        name: name of logger (module). Should provide `__name__`.
        settings:

    Returns:
        Logger with RotatingFileHandler.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level=settings.file_level)
    logger.handlers = []  # Remove all handlers

    try:
        settings.log_dir.mkdir()
    except FileExistsError:
        pass

    filename = settings.log_dir / f"{name}.log"
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


_LOG = get_file_logger(name=__name__, settings=LogSettings())


def log_exceptions(func: Callable) -> Any:
    """Decorator, logging function signature and exception if it occur."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        args_repr = [repr(a) for a in args]
        kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
        signature = ", ".join(args_repr + kwargs_repr)

        try:
            value = func(*args, **kwargs)
            return value
        except Exception as exc:  # pylint: disable=broad-except
            # TODO: more info
            # TODO: use extra
            _LOG.warning(
                "During %s(%s) call, exception %s: %s occurred",
                func.__name__,
                signature,
                exc.__class__.__name__,
                exc,
            )
            raise exc

    return wrapper

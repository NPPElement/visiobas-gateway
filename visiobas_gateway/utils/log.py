from __future__ import annotations

import asyncio
import logging
import typing
from functools import wraps
from logging.handlers import RotatingFileHandler
from typing import Any, Awaitable, Callable

from ..schemas.settings.log_settings import log_settings

_MEGABYTE = 10 ** 6

_EXC_INFO = log_settings.file_level == "DEBUG"


class ExtraFormatter(logging.Formatter):
    """Formatter for display `extra` params.

    Adopted from:
        <https://stackoverflow.com/questions/56559971/show-extra-fields-when-logging-to-console-in-python>
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


def get_file_logger(name: str) -> logging.Logger:
    """Gets Logger with RotatingFileHandler.

    Args:
        name: name of logger (module). Should provide `__name__`.

    Returns:
        Logger with RotatingFileHandler.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level=log_settings.file_level)
    logger.handlers = []  # Remove all handlers

    try:
        log_settings.log_dir.mkdir()
    except FileExistsError:
        pass

    filename = log_settings.log_dir / f"{name.removeprefix('visiobas_gateway.')}.log"
    size = log_settings.file_size + _MEGABYTE

    file_handler = RotatingFileHandler(
        filename=filename,
        mode="a",
        maxBytes=size,
        backupCount=1,
        encoding="utf-8",
    )
    formatter = ExtraFormatter(fmt=log_settings.format)
    file_handler.setFormatter(fmt=formatter)
    logger.addHandler(file_handler)

    return logger


def log_exceptions(
    logger: logging.Logger,
    func: Callable | Callable[..., typing.Awaitable] = None,  # type: ignore
    *,
    parameters_enabled: bool = True,
    exc_info: bool = _EXC_INFO,
) -> Any:
    def _log_exceptions(func: Callable | Callable[..., Awaitable]) -> Any:
        """Decorator, logging function signature and exception if it occur."""

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            if parameters_enabled:
                args_repr = [repr(a) for a in args]
                kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
                signature = ", ".join(args_repr + kwargs_repr)
            else:
                signature = "..."

            try:
                value = func(*args, **kwargs)
                return value
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning(
                    "During %s(%s) call, exception %s: %s occurred",
                    func.__name__,
                    signature,
                    exc.__class__.__name__,
                    exc,
                    exc_info=exc_info,
                )
                raise exc

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            if parameters_enabled:
                args_repr = [repr(a) for a in args]
                kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
                signature = ", ".join(args_repr + kwargs_repr)
            else:
                signature = "..."

            try:
                value = await func(*args, **kwargs)
                return value
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning(
                    "During %s(%s) call, exception %s: %s occurred",
                    func.__name__,
                    signature,
                    exc.__class__.__name__,
                    exc,
                    exc_info=exc_info,
                )
                raise exc

        return (
            async_wrapper
            if asyncio.iscoroutine(func) or asyncio.iscoroutinefunction(func)
            else sync_wrapper
        )

    if func:
        return _log_exceptions(func=func)
    return _log_exceptions

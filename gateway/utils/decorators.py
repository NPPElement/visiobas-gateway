from functools import wraps
from typing import Any, Callable

from ..models.settings.log_settings import LogSettings
from .log_file import get_file_logger

_LOG = get_file_logger(name=__name__, settings=LogSettings())


def log_exceptions(func: Callable) -> Any:
    """Logging function signature and exception if it occur."""

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

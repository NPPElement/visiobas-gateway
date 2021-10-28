from __future__ import annotations

import re
from typing import Any, Generator

# <https://en.wikipedia.org/wiki/Serial_port>
serial_port_regex = re.compile(r"/dev/tty(S\d{1,2}|USB\d)")


class SerialPort(str):
    """Serial port validation.

    Note: in particular this does NOT guarantee a serial port exists, just that it has a
    valid format.
    Only /dev/tty* format supported.
    """

    @classmethod
    def __get_validators__(cls) -> Generator:
        # one or more validators may be yielded which will be called in the
        # order to validate the input, each validator will receive as an input
        # the value returned from the previous validator
        yield cls.validate

    @classmethod
    def __modify_schema__(cls, field_schema: dict[str, Any]) -> None:
        # __modify_schema__ should mutate the dict it receives in place,
        # the returned value will be ignored
        field_schema.update(
            # simplified regex here for brevity, see the wikipedia link above
            pattern=r"/dev/tty(S\d{1,2}|USB\d)",
            # some example postcodes
            examples=["/dev/ttyS0", "/dev/ttyUSB1"],
        )

    @classmethod
    def validate(cls, v: str) -> SerialPort:
        if not isinstance(v, str):
            raise TypeError("`str` required")
        m = serial_port_regex.fullmatch(v)  # .upper()
        if not m:
            raise ValueError("Invalid serial port format")
        # you could also return a string here which would mean model.post_code
        # would be a string, pydantic won't care but you could end up with some
        # confusion since the value's type won't match the type annotation
        # exactly
        return cls(v)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({super().__repr__()})"

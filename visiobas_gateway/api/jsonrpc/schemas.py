from __future__ import annotations

from typing import Union

from pydantic import Field, validator

from ...schemas import BaseBACnetObj, ObjProperty, Priority


class RPCSetPointParams(BaseBACnetObj):
    """Common parameters for JSON-RPC methods."""

    name: str = Field(default="")
    priority: Priority = Field(...)
    property: ObjProperty = Field(...)

    @validator("property", pre=True)
    def cast_property(cls, value: str | int) -> ObjProperty:
        # pylint: disable=no-self-argument
        if isinstance(value, str):
            value = int(value)
        if isinstance(value, int):
            return ObjProperty(value)
        raise ValueError(f"Value must be `{ObjProperty}`. Got `{type(value)}`.")

    value: Union[int, float] = Field(...)

    @validator("value")
    def validate_value(cls, value: float | int | str) -> float | int:
        # pylint: disable=no-self-argument
        if isinstance(value, str):
            value = float(value)
        if isinstance(value, float):
            if value.is_integer():
                return int(value)
        return value
        # raise ValueError(f"Value must be number. Got `{type(value)}`.")

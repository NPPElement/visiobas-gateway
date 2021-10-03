from __future__ import annotations

import json
from abc import ABC
from typing import Any

from pydantic import BaseModel, Field, validator

from ...utils import snake_case
from .obj_property import ObjProperty
from .obj_type import ObjType


class BaseBACnetObj(BaseModel, ABC):
    """Base class for all BACnet objects."""

    # for evident exception use code below + validation
    # # type: Union[int, str] = Field(..., alias=ObjProperty.objectType.id_str)
    object_type: ObjType = Field(
        ...,
        alias=str(ObjProperty.OBJECT_TYPE.value),
        description="""Indicates membership in a particular object type class.""",
    )

    @validator("object_type", pre=True)
    def validate_type(cls, value: int | str) -> ObjType:
        # pylint: disable=no-self-argument
        if isinstance(value, int):
            return ObjType(value)
        if isinstance(value, str):
            if value.isdigit():
                return ObjType(int(value))
            try:
                return ObjType[snake_case(value).upper()]
            except KeyError:
                pass
        raise ValueError("Invalid type")

    device_id: int = Field(..., gt=0, alias=str(ObjProperty.DEVICE_ID.value))
    object_id: int = Field(
        ...,
        ge=0,
        alias=str(ObjProperty.OBJECT_IDENTIFIER.value),
        description="""Is a numeric code that is used to identify the object.
        It shall be unique within the BACnet Device that maintains it.""",
    )
    name: str = Field(
        ...,
        alias=str(ObjProperty.OBJECT_NAME.value),
        min_length=1,
        description="""Represent a name for the object that is unique within the
        BACnet Device that maintains it. The minimum length of the string shall be one
        character. The set of characters used in the Object_Name shall be restricted to
        printable characters.""",
    )
    property_list: Any = Field(alias=str(ObjProperty.PROPERTY_LIST.value))

    @validator("property_list", pre=True)
    def parse_property_list(cls, value: str) -> str:
        # pylint: disable=no-self-argument
        return json.loads(value)

    @property
    def mqtt_topic(self) -> str:
        """Replaces `:.` by `/` (MQTT topic)."""
        return self.name.replace(":", "/").replace(".", "/")

    def __hash__(self) -> int:
        return hash((self.object_type, self.object_id, self.device_id))

    class Config:  # pylint: disable=missing-class-docstring
        allow_population_by_field_name = True

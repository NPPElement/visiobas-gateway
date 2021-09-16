from typing import Any, Union

from pydantic import BaseModel, Field, validator

from ...utils import snake_case
from .obj_property import ObjProperty
from .obj_type import ObjType


class BaseBACnetObj(BaseModel):
    """Base class for all BACnet objects."""

    # for evident exception use code below + validation
    # # type: Union[int, str] = Field(..., alias=ObjProperty.objectType.id_str)
    type: ObjType = Field(
        ...,
        alias=str(ObjProperty.OBJECT_TYPE.id),
        description="""Indicates membership in a particular object type class.""",
    )
    device_id: int = Field(..., gt=0, alias=str(ObjProperty.DEVICE_ID.id))
    id: int = Field(
        ...,
        ge=0,
        alias=str(ObjProperty.OBJECT_IDENTIFIER.id),
        description="""Is a numeric code that is used to identify the object.
        It shall be unique within the BACnet Device that maintains it.""",
    )
    name: str = Field(
        ...,
        alias=str(ObjProperty.OBJECT_NAME.id),
        min_length=1,
        description="""Represent a name for the object that is unique within the
        BACnet Device that maintains it. The minimum length of the string shall be one
        character. The set of characters used in the Object_Name shall be restricted to
        printable characters.""",
    )
    property_list: Any = Field(alias=str(ObjProperty.PROPERTY_LIST.id))

    @validator("type", pre=True)
    def validate_type(cls, value: Union[int, str]) -> ObjType:
        # pylint: disable=no-self-argument
        if isinstance(value, int):
            return ObjType(value)
        if isinstance(value, str):
            try:
                return ObjType[snake_case(value).upper()]
            except KeyError:
                pass
        raise ValueError("Invalid type")

    @property
    def mqtt_topic(self) -> str:
        """Replaces `:.` by `/` (MQTT topic)."""
        return self.name.replace(":", "/").replace(".", "/")

    def __hash__(self) -> int:
        return hash((self.type, self.id, self.device_id))

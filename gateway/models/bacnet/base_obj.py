from typing import Any

from pydantic import BaseModel, Field

from .obj_property import ObjProperty
from .obj_type import ObjType


class BaseBACnetObjModel(BaseModel):
    """Base class for all BACnet objects."""

    # for evident exception use code below + validation
    # # type: Union[int, str] = Field(..., alias=ObjProperty.objectType.id_str)
    type: ObjType = Field(
        ...,
        alias=str(ObjProperty.objectType.id),
        description="""
    Indicates membership in a particular object type class.""",
    )

    device_id: int = Field(..., gt=0, alias=str(ObjProperty.deviceId.id))
    id: int = Field(
        ...,
        ge=0,
        alias=str(ObjProperty.objectIdentifier.id),
        description="""Is a numeric code that is used to identify the object.
        It shall be unique within the BACnet Device that maintains it.""",
    )

    name: str = Field(
        ...,
        alias=str(ObjProperty.objectName.id),
        min_length=1,
        description="""Represent a name for the object that is unique within the
        BACnet Device that maintains it. The minimum length of the string shall be one
        character. The set of characters used in the Object_Name shall be restricted to
        printable characters.""",
    )

    property_list: Any = Field(alias=str(ObjProperty.propertyList.id))

    @property
    def replaced_name(self) -> str:
        return self.name.replace(":", "/").replace(".", "/")

    @property
    def mqtt_topic(self) -> str:
        return self.replaced_name

    def __hash__(self) -> int:
        return hash((self.type, self.id, self.device_id))

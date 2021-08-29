from pydantic import BaseModel, Field, Json

from .obj_property import ObjProperty
from .obj_type import ObjType


class BaseBACnetObjModel(BaseModel):
    # for evident exception use code below + validation
    # # type: Union[int, str] = Field(..., alias=ObjProperty.objectType.id_str)
    type: ObjType = Field(
        ...,
        alias=ObjProperty.objectType.id_str,
        description="""
    Indicates membership in a particular object type class.""",
    )

    device_id: int = Field(..., gt=0, alias=ObjProperty.deviceId.id_str)
    id: int = Field(
        ...,
        ge=0,
        alias=ObjProperty.objectIdentifier.id_str,
        description="""Is a numeric code that is used to identify the object.
        It shall be unique within the BACnet Device that maintains it.""",
    )

    name: str = Field(
        ...,
        alias=ObjProperty.objectName.id_str,
        min_length=1,
        description="""Represent a name for the object that is unique within the
        BACnet Device that maintains it. The minimum length of the string shall be one
        character. The set of characters used in the Object_Name shall be restricted to
        printable characters.""",
    )

    property_list: Json = Field(alias=ObjProperty.propertyList.id_str)

    @property
    def replaced_name(self) -> str:
        return self.name.replace(":", "/").replace(".", "/")

    @property
    def mqtt_topic(self) -> str:
        return self.replaced_name

    def __hash__(self) -> int:
        return hash((self.type, self.id, self.device_id))

from typing import Union

from pydantic import BaseModel, Field, validator

from .obj_property import ObjProperty
from .obj_type import ObjType


class BACnetObjModel(BaseModel):
    # for evident exception use code below + validation
    # # type: Union[int, str] = Field(..., alias=ObjProperty.objectType.id_str)
    type: ObjType = Field(..., alias=ObjProperty.objectType.id_str)

    device_id: int = Field(..., gt=0, alias=ObjProperty.deviceId.id_str)

    id: int = Field(..., ge=0, alias=ObjProperty.objectIdentifier.id_str)
    name: str = Field(..., alias=ObjProperty.objectName.id_str)

    # property_list: str = Field(alias=ObjProperty.propertyList.id_str)

    # status_flags: Union[list[bool], None] = Field(alias=ObjProperty.statusFlags.id_str)
    # priority_array: Union[str, None] = Field(alias=ObjProperty.priorityArray.id_str)
    # reliability: Union[str, None] = Field(alias=ObjProperty.reliability.id_str)

    resolution: Union[float, int, None] = Field(alias=ObjProperty.resolution.id_str)
    upd_interval: Union[float, int, None] = Field(alias=ObjProperty.updateInterval.id_str)
    present_value: float = Field(alias=ObjProperty.presentValue.id_str)

    _last_value = None

    # @validator('type')
    # def cast_to_obj_type(cls, v):
    #     print(type(v), v)
    #     return ObjType(v)

    @validator('resolution')
    def set_default_resolution(cls, v):
        return v or .1

    # @validator('property_list')
    # def parse_property_list(cls, v):
    #     return PropertyListModel.parse_raw(v)

    @property
    def topic(self):
        return self.name.replace(':', '/').replace('.', '/')


# class BACnetObjectsDataModel(BaseModel):
#     success: bool = Field(default=...)
#     data: list[BACnetObjModel] = Field(default=...)
#
#     @validator('success')
#     def successful(cls, v):
#         if v:
#             return v
#         raise ValueError('Must be True')
#
#     @validator('')


# class BACnetObj(NamedTuple):
#     # type: ObjType
#     id: int
#
#     name: str
#     resolution: float = None  # todo
#     update_interval: int = None  # TODO: implement skip by update_interval
#
#     @property
#     def topic(self):
#         return self.name.replace(':', '/').replace('.', '/')
#
#     @classmethod
#     def from_dict(cls, obj_type: ObjType, obj_props: dict):
#         obj_id = obj_props[str(ObjProperty.objectIdentifier.id)]
#         obj_name = obj_props[str(ObjProperty.objectName.id)]
#
#         return cls(type=obj_type,
#                    id=obj_id,
#                    name=obj_name
#                    )

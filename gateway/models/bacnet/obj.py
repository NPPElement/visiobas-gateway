from typing import Union

from pydantic import Field

from .base_obj import BaseBACnetObjModel
from .obj_property import ObjProperty


class BACnetObjModel(BaseBACnetObjModel):
    # present_value: float = Field(alias=ObjProperty.presentValue.id_str)
    # status_flags: Union[list[bool], None] = Field(alias=ObjProperty.statusFlags.id_str)
    # priority_array: Union[str, None] = Field(alias=ObjProperty.priorityArray.id_str)
    # reliability: Union[str, None] = Field(alias=ObjProperty.reliability.id_str)

    resolution: Union[float, int, None] = Field(default=0.1,
                                                alias=ObjProperty.resolution.id_str)
    upd_interval: Union[float, int, None] = Field(default=60,
                                                  alias=ObjProperty.updateInterval.id_str)
    segmentation_supported: bool = Field(default=False,
                                         alias=ObjProperty.segmentationSupported.id_str)

    _last_value = None

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

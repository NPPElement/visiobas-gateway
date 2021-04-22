from typing import Optional

from pydantic import Field, validator

from .base_obj import BaseBACnetObjModel
from .obj_property import ObjProperty


class BACnetObjModel(BaseBACnetObjModel):
    # present_value: float = Field(alias=ObjProperty.presentValue.id_str)
    # status_flags: Union[list[bool], None] = Field(alias=ObjProperty.statusFlags.id_str)
    # priority_array: Union[str, None] = Field(alias=ObjProperty.priorityArray.id_str)
    # reliability: Union[str, None] = Field(alias=ObjProperty.reliability.id_str)

    resolution: Optional[float] = Field(default=0.1, alias=ObjProperty.resolution.id_str)
    poll_interval: Optional[float] = Field(default=60,
                                           alias=ObjProperty.updateInterval.id_str)
    send_interval: int = Field(default=60)
    segmentation_supported: bool = Field(default=False,
                                         alias=ObjProperty.segmentationSupported.id_str)

    _last_value = None

    def __repr__(self) -> str:
        return f'BACnetObj{self.__dict__}'

    @validator('poll_interval')  # todo deprecate
    def set_default_poll_interval(cls, v):
        return v or 60

    @validator('resolution')  # todo deprecate
    def set_default_resolution(cls, v):
        return v or 0.1

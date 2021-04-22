from typing import Optional

from pydantic import Field, validator, BaseModel

from .base_obj import BaseBACnetObjModel
from .obj_property import ObjProperty


class BACnetObjPropertyListModel(BaseModel):
    poll_interval: float = Field(default=60, alias='pollInterval',
                                 description='Period to internal object poll')

    def __repr__(self) -> str:
        return str(self.__dict__)


class BACnetObjPropertyListJsonModel(BaseModel):
    property_list: BACnetObjPropertyListModel = Field(default=None)

    def __repr__(self) -> str:
        return str(self.__dict__)


class BACnetObjModel(BaseBACnetObjModel):
    # present_value: float = Field(alias=ObjProperty.presentValue.id_str)
    # status_flags: Union[list[bool], None] = Field(alias=ObjProperty.statusFlags.id_str)
    # priority_array: Union[str, None] = Field(alias=ObjProperty.priorityArray.id_str)
    # reliability: Union[str, None] = Field(alias=ObjProperty.reliability.id_str)

    resolution: Optional[float] = Field(default=0.1, alias=ObjProperty.resolution.id_str)

    # todo find public property
    # send_interval: Optional[float] = Field(default=60,
    #                                        alias=ObjProperty.updateInterval.id_str)

    segmentation_supported: bool = Field(default=False,
                                         alias=ObjProperty.segmentationSupported.id_str)
    property_list: BACnetObjPropertyListJsonModel = Field(
        ..., alias=ObjProperty.propertyList.id_str)

    _last_value = None

    def __repr__(self) -> str:
        return f'BACnetObj{self.__dict__}'

    # @validator('poll_interval')
    # def set_default_poll_interval(cls, v):
    #     return v or 60

    @validator('resolution')  # todo deprecate
    def set_default_resolution(cls, v):
        return v or 0.1

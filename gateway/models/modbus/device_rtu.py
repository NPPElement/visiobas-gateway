from pydantic import Field, validator

from .device_rtu_property_list import (DeviceRTUPropertyListModel,
                                       DeviceRTUPropertyListWrapper)
from ..bacnet.device_obj import BACnetDeviceModel
from ..bacnet.obj_property import ObjProperty


class ModbusRTUDeviceModel(BACnetDeviceModel):
    property_list: DeviceRTUPropertyListWrapper = Field(
        alias=ObjProperty.propertyList.id_str)

    @validator('property_list')
    def parse_rtu_pl(cls, pl: str) -> DeviceRTUPropertyListModel:
        return DeviceRTUPropertyListModel.parse_raw(pl)

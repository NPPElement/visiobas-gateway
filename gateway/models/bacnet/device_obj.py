from pydantic import Field, validator

from .base_obj import BaseBACnetObjModel
from .obj_property import ObjProperty
from ..modbus.device_rtu_property_list import (DeviceRTUPropertyListWrapper,
                                               DeviceRTUPropertyListModel)


class BACnetDeviceModel(BaseBACnetObjModel):
    timeout: int = Field(..., alias=ObjProperty.apduTimeout.id_str)
    retries: int = Field(default=1, alias=ObjProperty.numberOfApduRetries.id_str)

    # todo use Ip obj
    address: str = Field(..., alias=ObjProperty.deviceAddressBinding.id_str)

    # todo use Protocol Enum
    protocol: str = Field(..., alias=ObjProperty.protocolVersion.id_str)

    # todo refactor
    property_list: DeviceRTUPropertyListWrapper = Field(
        alias=ObjProperty.propertyList.id_str)

    @validator('property_list')
    def parse_rtu_pl(cls, pl: str) -> DeviceRTUPropertyListModel:
        return DeviceRTUPropertyListModel.parse_raw(pl)

    # send_sync_delay = # send period
    # internal_sync_delay =

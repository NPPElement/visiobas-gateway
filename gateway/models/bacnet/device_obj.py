from typing import Union

from pydantic import Field, validator, BaseModel

from .base_obj import BaseBACnetObjModel
from .obj_property import ObjProperty


# from ..modbus.device_rtu_property_list import DeviceRTUPropertyListModel


class DeviceRTUPropertyListModel(BaseModel):
    port: str = Field(...)
    baudrate: int = Field(..., gt=0, lt=115200)
    stopbits: int = Field(default=1)
    bytesize: int = Field(default=8)
    timeout: float = Field(default=1)
    parity: str = Field(default='N')


class DevicePropertyListWrapper(BaseModel):
    rtu: DeviceRTUPropertyListModel


class BACnetDeviceModel(BaseBACnetObjModel):
    timeout: int = Field(..., alias=ObjProperty.apduTimeout.id_str)
    retries: int = Field(default=1, alias=ObjProperty.numberOfApduRetries.id_str)

    address: str = Field(...,
                         alias=ObjProperty.deviceAddressBinding.id_str)  # todo use Ip obj
    protocol: str = Field(...,
                          alias=ObjProperty.protocolVersion.id_str)  # todo use Protocol Enum

    # todo refactor
    property_list: Union[str, DevicePropertyListWrapper] = Field(
        alias=ObjProperty.propertyList.id_str)

    @validator('property_list')
    def parse_rtu_pl(cls, pl: str) -> DevicePropertyListWrapper:
        return DevicePropertyListWrapper.parse_raw(pl)

    # send_sync_delay = # send period
    # internal_sync_delay =

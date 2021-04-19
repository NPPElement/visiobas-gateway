from typing import Union

from pydantic import Field, validator, BaseModel
from pymodbus.constants import Defaults

from .base_obj import BaseBACnetObjModel
from .obj_property import ObjProperty
from .obj_type import ObjType


# from ..modbus.device_rtu_property_list import DeviceRTUPropertyListModel


class DeviceRTUPropertyListModel(BaseModel):
    port: str = Field(default=Defaults.Port)
    baudrate: int = Field(default=Defaults.Baudrate, gt=0, lt=115200)
    stopbits: int = Field(default=Defaults.Stopbits)
    bytesize: int = Field(default=Defaults.Bytesize)
    timeout: float = Field(default=1)  # 3s is too much
    parity: str = Field(default=Defaults.Parity)


class DevicePropertyListWrap(BaseModel):
    rtu: DeviceRTUPropertyListModel = Field(default=None)
    address: str = Field(default=None)  # todo use Ip objs


class BACnetDeviceModel(BaseBACnetObjModel):
    timeout: int = Field(..., alias=ObjProperty.apduTimeout.id_str)
    retries: int = Field(default=2, alias=ObjProperty.numberOfApduRetries.id_str)

    # address: str = Field(...,
    #                      alias=ObjProperty.deviceAddressBinding.id_str)

    # todo Enum for protocols
    # protocol: str = Field(...,
    #                       alias=ObjProperty.protocolVersion.id_str)

    # send_sync_delay = # send period
    # internal_sync_delay =

    # todo refactor
    property_list: Union[str, DevicePropertyListWrap] = Field(
        alias=ObjProperty.propertyList.id_str)

    @validator('property_list')
    def parse_rtu_pl(cls, pl: str) -> DevicePropertyListWrap:
        return DevicePropertyListWrap.parse_raw(pl)

    @property
    def types_to_rq(self) -> tuple[ObjType, ...]:
        return (ObjType.ANALOG_INPUT, ObjType.ANALOG_OUTPUT, ObjType.ANALOG_VALUE,
                ObjType.BINARY_INPUT, ObjType.BINARY_OUTPUT, ObjType.BINARY_VALUE,
                ObjType.MULTI_STATE_INPUT, ObjType.MULTI_STATE_OUTPUT,
                ObjType.MULTI_STATE_VALUE, )



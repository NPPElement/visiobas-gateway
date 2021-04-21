from ipaddress import IPv4Address
from typing import Union

from pydantic import Field, validator, BaseModel, Json
from pymodbus.constants import Defaults

from .base_obj import BaseBACnetObjModel
from .obj_property import ObjProperty
from .obj_type import ObjType


class DeviceRTUPropertyListModel(BaseModel):
    unit: int = Field(...)  # address of serial device
    port: str = Field(...)  # interface for serial devices
    baudrate: int = Field(default=Defaults.Baudrate, gt=0, lt=115200)
    stopbits: int = Field(default=Defaults.Stopbits)
    bytesize: int = Field(default=Defaults.Bytesize)
    timeout: float = Field(default=1)  # 3s is too much
    parity: str = Field(default=Defaults.Parity)
    retry_on_empty: bool = Field(default=True)  # works better
    retry_on_invalid: bool = Field(default=True)  # works better

    def __repr__(self) -> str:
        return str(self.__dict__)


class DevicePropertyListWrap(BaseModel):
    rtu: DeviceRTUPropertyListModel = Field(default=None)
    protocol: str = Field(...)  # todo Enum for protocols
    address: IPv4Address = Field(default=None)

    def __repr__(self) -> str:
        return str(self.__dict__)


class BACnetDeviceModel(BaseBACnetObjModel):
    timeout: int = Field(..., alias=ObjProperty.apduTimeout.id_str)
    retries: int = Field(default=2, alias=ObjProperty.numberOfApduRetries.id_str)

    # send_sync_delay = # send period
    # internal_sync_delay =

    # todo refactor
    property_list: Json[DevicePropertyListWrap] = Field(
        alias=ObjProperty.propertyList.id_str)

    # @validator('property_list')
    # def parse_rtu_pl(cls, pl: str) -> DevicePropertyListWrap:
    #     return DevicePropertyListWrap.parse_raw(pl)

    @property
    def types_to_rq(self) -> tuple[ObjType, ...]:
        return (ObjType.ANALOG_INPUT, ObjType.ANALOG_OUTPUT, ObjType.ANALOG_VALUE,
                ObjType.BINARY_INPUT, ObjType.BINARY_OUTPUT, ObjType.BINARY_VALUE,
                ObjType.MULTI_STATE_INPUT, ObjType.MULTI_STATE_OUTPUT,
                ObjType.MULTI_STATE_VALUE,)

    def __repr__(self) -> str:
        return f'DeviceObj{self.__dict__}'

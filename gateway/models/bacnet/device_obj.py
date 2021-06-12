from ipaddress import IPv4Address
from typing import Optional

from pydantic import Field, BaseModel, Json, validator
from pymodbus.constants import Defaults

from .base_obj import BaseBACnetObjModel
from .obj_property import ObjProperty
from .obj_type import ObjType
from ..protocol import Protocol


class DeviceRTUPropertyListModel(BaseModel):
    unit: int = Field(...)  # address of serial device
    port: Optional[str] = Field(default=None)  # interface for serial devices
    baudrate: int = Field(default=9600, gt=0, lt=115200)  # default=Defaults.Baudrate
    stopbits: int = Field(default=Defaults.Stopbits)
    bytesize: int = Field(default=Defaults.Bytesize)
    # timeout: float = Field(default=1)  # 3s is too much
    parity: str = Field(default=Defaults.Parity)

    def __str__(self) -> str:
        return str(self.__dict__)

    def __repr__(self) -> str:
        return str(self)


class DevicePropertyListJsonModel(BaseModel):
    protocol: Protocol = Field(...)
    rtu: Optional[DeviceRTUPropertyListModel] = Field(default=None)
    address: Optional[IPv4Address] = Field(default=None)
    port: Optional[int] = Field(default=None)

    # todo check
    internal_period: float = Field(default=0.3, alias='internalPeriod')
    reconnect_period: int = Field(default=5 * 60, alias='reconnectPeriod')

    def __str__(self) -> str:
        return str(self.__dict__)

    def __repr__(self) -> str:
        return str(self)

    @validator('rtu')
    def port_in_rtu_required(cls, v: DeviceRTUPropertyListModel, values):
        if values['protocol'] is Protocol.MODBUS_RTU and not v.port:
            raise ValueError('ModbusRTU required port')
        return v


class BACnetDeviceObj(BaseBACnetObjModel):
    timeout: int = Field(
        default=6000, alias=ObjProperty.apduTimeout.id_str, gt=0,
        description='''
        The amount of time in milliseconds between retransmissions of an APDU requiring 
        acknowledgment for which no acknowledgment has been received. A suggested default 
        value for this property is 6,000 milliseconds for devices that permit modification 
        of this parameter. Otherwise, the default value shall be 10,000 milliseconds. 
        This value shall be non-zero if the Device object property called 
        Number_Of_APDU_Retries is non-zero.''')
    retries: int = Field(
        default=3, alias=ObjProperty.numberOfApduRetries.id_str, ge=0,
        description='''
        Indicates the maximum number of times that an APDU shall be retransmitted. 
        A suggested default value for this property is 3. If this device does not perform 
        retries, then this property shall be set to zero. If the value of this property is 
        greater than zero, a non-zero value shall be placed in the Device object 
        APDU_Timeout property.''')

    # send_sync_delay = # send period
    # internal_sync_delay =

    property_list: Json[DevicePropertyListJsonModel] = Field(
        ..., alias=ObjProperty.propertyList.id_str)

    def __str__(self) -> str:
        return self.__class__.__name__ + str(self.__dict__)

    def __repr__(self) -> str:
        return str(self)

    @property
    def types_to_rq(self) -> tuple[ObjType, ...]:
        return (ObjType.ANALOG_INPUT, ObjType.ANALOG_OUTPUT, ObjType.ANALOG_VALUE,
                ObjType.BINARY_INPUT, ObjType.BINARY_OUTPUT, ObjType.BINARY_VALUE,
                ObjType.MULTI_STATE_INPUT, ObjType.MULTI_STATE_OUTPUT,
                ObjType.MULTI_STATE_VALUE,)

    @property
    def protocol(self) -> Protocol:
        return self.property_list.protocol

    @property
    def timeout_sec(self) -> float:
        return self.timeout / 1000

    @property
    def baudrate(self) -> Optional[int]:
        if self.protocol is Protocol.MODBUS_RTU:
            return self.property_list.rtu.baudrate

    @property
    def bytesize(self) -> Optional[int]:
        if self.protocol is Protocol.MODBUS_RTU:
            return self.property_list.rtu.bytesize

    @property
    def parity(self) -> Optional[str]:
        if self.protocol is Protocol.MODBUS_RTU:
            return self.property_list.rtu.parity

    @property
    def stopbits(self) -> Optional[int]:
        if self.protocol is Protocol.MODBUS_RTU:
            return self.property_list.rtu.stopbits

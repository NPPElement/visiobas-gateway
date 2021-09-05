from typing import Optional, Union

from pydantic import Field

from ..modbus import BaudRate, Bytesize, Parity, StopBits
from ..protocol import Protocol
from .base_obj import BaseBACnetObj
from .device_property_list import SerialDevicePropertyList, TcpIpDevicePropertyList
from .obj_property import ObjProperty
from .obj_type import ObjType


class DeviceObj(BaseBACnetObj):
    """Represent device object."""

    property_list: Union[TcpIpDevicePropertyList, SerialDevicePropertyList] = Field(
        ..., alias=str(ObjProperty.propertyList.prop_id)
    )

    @property
    def types_to_rq(self) -> tuple[ObjType, ...]:
        return (
            ObjType.ANALOG_INPUT,
            ObjType.ANALOG_OUTPUT,
            ObjType.ANALOG_VALUE,
            ObjType.BINARY_INPUT,
            ObjType.BINARY_OUTPUT,
            ObjType.BINARY_VALUE,
            ObjType.MULTI_STATE_INPUT,
            ObjType.MULTI_STATE_OUTPUT,
            ObjType.MULTI_STATE_VALUE,
        )

    @property
    def protocol(self) -> Protocol:
        return self.property_list.protocol

    @property
    def timeout_sec(self) -> float:
        return self.property_list.timeout / 1000

    @property
    def retries(self) -> int:
        return self.property_list.retries

    @property
    def baudrate(self) -> Optional[BaudRate]:
        if hasattr(self.property_list, "rtu"):
            return self.property_list.rtu.baudrate  # type: ignore
        return None

    @property
    def bytesize(self) -> Optional[Bytesize]:
        if hasattr(self.property_list, "rtu"):
            return self.property_list.rtu.bytesize  # type: ignore
        return None

    @property
    def parity(self) -> Optional[Parity]:
        if hasattr(self.property_list, "rtu"):
            return self.property_list.rtu.parity  # type: ignore
        return None

    @property
    def stopbits(self) -> Optional[StopBits]:
        if hasattr(self.property_list, "rtu"):
            return self.property_list.rtu.stopbits  # type: ignore
        return None

from typing import Union

from pydantic import Field

from ..modbus.device_property_list import (
    ModbusTcpDevicePropertyList,
    SerialDevicePropertyList,
)
from .base_obj import BaseBACnetObj
from .device_property_list import TcpDevicePropertyList
from .obj_property import ObjProperty
from .obj_type import ObjType


class DeviceObj(BaseBACnetObj):
    """Represent device object."""

    property_list: Union[
        ModbusTcpDevicePropertyList,
        TcpDevicePropertyList,
        SerialDevicePropertyList,
    ] = Field(  # type: ignore
        ..., alias=str(ObjProperty.PROPERTY_LIST.value)
    )


# class BACnetDeviceObj(DeviceObj):
#     """Device object for BACnet devices."""
#
#     property_list: TcpDevicePropertyList = Field(
#         ..., alias=str(ObjProperty.PROPERTY_LIST.value)
#     )


POLLING_TYPES = (
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

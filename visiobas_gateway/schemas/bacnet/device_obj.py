from typing import Union

from pydantic import Field

from .base_obj import BaseBACnetObj
from .device_property_list import (
    SerialDevicePropertyList,
    TcpIpDevicePropertyList,
    TcpIpModbusDevicePropertyList,
)
from .obj_property import ObjProperty
from .obj_type import ObjType


class DeviceObj(BaseBACnetObj):
    """Represent device object."""

    property_list: Union[
        TcpIpModbusDevicePropertyList,
        TcpIpDevicePropertyList,
        SerialDevicePropertyList,
    ] = Field(  # type: ignore
        ..., alias=str(ObjProperty.PROPERTY_LIST.id)
    )


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

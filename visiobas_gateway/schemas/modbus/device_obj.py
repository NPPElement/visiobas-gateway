from pydantic import Field

from ..bacnet.device_obj import DeviceObj
from ..bacnet.obj_property import ObjProperty
from .device_property_list import ModbusTcpDevicePropertyList, SerialDevicePropertyList


class ModbusTCPDeviceObj(DeviceObj):
    """Device object for Modbus over TCP devices."""

    property_list: ModbusTcpDevicePropertyList = Field(
        ..., alias=str(ObjProperty.PROPERTY_LIST.value)
    )


class ModbusSerialDeviceObj(DeviceObj):
    """Device object for Modbus serial devices."""

    property_list: SerialDevicePropertyList = Field(
        ..., alias=str(ObjProperty.PROPERTY_LIST.value)
    )

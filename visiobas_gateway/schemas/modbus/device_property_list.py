from pydantic import Field, validator

from ..bacnet.device_property_list import BaseDevicePropertyList, TcpDevicePropertyList
from ..protocol import MODBUS_TCP_IP_PROTOCOLS, SERIAL_PROTOCOLS, Protocol
from ..serial_port import SerialPort
from .device_rtu_properties import BaseDeviceModbusProperties, DeviceRtuProperties


class ModbusTcpDevicePropertyList(TcpDevicePropertyList):
    """PropertyList for TCP/IP Modbus devices."""

    rtu: BaseDeviceModbusProperties = Field(default=BaseDeviceModbusProperties(unit=1))
    # fixme: hotfix. Should be required. Not default!

    @validator("protocol")
    def validate_protocol(cls, value: Protocol) -> Protocol:
        # pylint: disable=no-self-argument
        if value in MODBUS_TCP_IP_PROTOCOLS:
            return value
        raise ValueError(f"Expected {MODBUS_TCP_IP_PROTOCOLS}")


class SerialDevicePropertyList(BaseDevicePropertyList):
    """PropertyList for Serial devices."""

    rtu: DeviceRtuProperties = Field(default=None)

    @validator("protocol")
    def validate_protocol(cls, value: Protocol) -> Protocol:
        # pylint: disable=no-self-argument
        if value in SERIAL_PROTOCOLS:
            return value
        raise ValueError(f"Expected {SERIAL_PROTOCOLS}")

    @property
    def interface(self) -> SerialPort:
        return self.rtu.port

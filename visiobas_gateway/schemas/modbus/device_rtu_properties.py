from pydantic import BaseModel, Field

from ..serial_port import SerialPort
from .baudrate import BaudRate
from .bytesize import Bytesize
from .parity import Parity
from .stopbits import StopBits


class BaseDeviceModbusProperties(BaseModel):
    """Represent RTU properties for Modbus TCP/IP devices."""

    unit: int = Field(..., ge=0, le=255, description="Address of serial device.")


class DeviceRtuProperties(BaseDeviceModbusProperties):
    """Represent RTU properties for ModbusRTU devices."""

    port: SerialPort = Field(..., description="Interface for serial device.")
    baudrate: BaudRate = Field(default=BaudRate._9600)  # pylint: disable=protected-access
    stopbits: StopBits = Field(default=StopBits._1)  # pylint: disable=protected-access
    bytesize: Bytesize = Field(default=Bytesize._8)  # pylint: disable=protected-access
    parity: Parity = Field(default=Parity.NONE)

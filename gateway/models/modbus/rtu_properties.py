from pydantic import BaseModel, Field

from .baudrate import BaudRate
from .bytesize import Bytesize
from .parity import Parity
from .stopbits import StopBits


class RtuProperties(BaseModel):
    """Represent RTU properties for ModbusRTU devices."""

    unit: int = Field(..., ge=0, description="Address of serial device")
    port: str = Field(..., description="Interface for serial devices")
    baudrate: BaudRate = Field(default=BaudRate._9600)  # pylint: disable=protected-access
    stopbits: StopBits = Field(default=StopBits._1)  # pylint: disable=protected-access
    bytesize: Bytesize = Field(default=Bytesize._8)  # pylint: disable=protected-access
    parity: Parity = Field(default=Parity.NONE)

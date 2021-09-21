from ipaddress import IPv4Address

from pydantic import Field, validator

from ..modbus import DeviceRtuProperties
from ..protocol import SERIAL_PROTOCOLS, TCP_IP_PROTOCOLS, Protocol
from .obj_property_list import BACnetObjPropertyList


class BaseDevicePropertyList(BACnetObjPropertyList):
    """Base class for PropertyList's (371) of device."""

    protocol: Protocol = Field(...)
    timeout: int = Field(
        default=6000,
        alias="apduTimeout",
        gt=0,  # alias=ObjProperty.apduTimeout.id_str
        description="""The amount of time in milliseconds between retransmissions of an
        APDU requiring acknowledgment for which no acknowledgment has been received.
        A suggested default value for this property is 6,000 milliseconds for devices that
        permit modification of this parameter. Otherwise, the default value shall be
        10,000 milliseconds. This value shall be non-zero if the Device object property
        named Number_Of_APDU_Retries is non-zero.""",
    )
    retries: int = Field(
        default=3,
        alias="numberOfApduRetries",
        ge=0,
        # alias=ObjProperty.numberOfApduRetries.id_str
        description="""Indicates the maximum number of times that an APDU shall be
        retransmitted. A suggested default value for this property is 3. If this device
        does not perform retries, then this property shall be set to zero. If the value of
        this property is greater than zero, a non-zero value shall be placed in the Device
        object APDU_Timeout property.""",
    )
    # fixme: add usage
    send_period: float = Field(
        default=300, alias="sendPeriod", description="Period to internal object poll."
    )
    # poll_period: float = Field(
    #     default=90, alias="pollPeriod", description="Period to send data to server."
    # )
    reconnect_period: int = Field(default=300, alias="reconnectPeriod")

    @property
    def timeout_seconds(self) -> float:
        """Timeout in seconds."""
        return self.timeout / 1000


class TcpIpDevicePropertyList(BaseDevicePropertyList):
    """PropertyList for TCP/IP devices."""

    address: IPv4Address = Field(default=None)
    port: int = Field(default=None)

    @validator("protocol")
    def validate_protocol(cls, value: Protocol) -> Protocol:
        # pylint: disable=no-self-argument
        if value in TCP_IP_PROTOCOLS:
            return value
        raise ValueError("Protocol is not TCP/IP")

    @property
    def address_port(self) -> str:
        return ":".join(
            (
                str(self.address), str(self.port),  # type: ignore
            )
        )


class SerialDevicePropertyList(BaseDevicePropertyList):
    """PropertyList for Serial devices."""

    rtu: DeviceRtuProperties = Field(default=None)

    @validator("protocol")
    def validate_protocol(cls, value: Protocol) -> Protocol:
        # pylint: disable=no-self-argument
        if value in SERIAL_PROTOCOLS:
            return value
        raise ValueError("Protocol is not Serial")

from __future__ import annotations

from abc import ABC, abstractmethod
from ipaddress import IPv4Address

from pydantic import Field, validator

from ..protocol import MODBUS_TCP_IP_PROTOCOLS, TCP_IP_PROTOCOLS, Protocol
from ..serial_port import SerialPort
from .obj_property_list import BACnetObjPropertyList


class BaseDevicePropertyList(BACnetObjPropertyList, ABC):
    """Base class for PropertyList's (371) of device."""

    protocol: Protocol = Field(...)
    timeout: int = Field(
        default=6000,
        alias="apduTimeout",
        gt=0,
        le=10_000,  # alias=ObjProperty.apduTimeout.id_str
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
        le=3,
        # alias=ObjProperty.numberOfApduRetries.id_str
        description="""Indicates the maximum number of times that an APDU shall be
        retransmitted. A suggested default value for this property is 3. If this device
        does not perform retries, then this property shall be set to zero. If the value of
        this property is greater than zero, a non-zero value shall be placed in the Device
        object APDU_Timeout property.""",
    )
    # fixme: add usage
    send_period: float = Field(
        default=300, ge=0, alias="sendPeriod", description="Period to internal object poll."
    )
    # poll_period: float = Field(
    #     default=90, alias="pollPeriod", description="Period to send data to server."
    # )
    reconnect_period: int = Field(default=300, ge=0, alias="reconnectPeriod")

    @property
    def timeout_seconds(self) -> float:
        """Timeout in seconds."""
        return self.timeout / 1000

    @property
    @abstractmethod
    def interface(self) -> tuple[IPv4Address, int] | SerialPort:
        """Interface to interaction with device."""


class TcpDevicePropertyList(BaseDevicePropertyList):
    """PropertyList for TCP/IP devices."""

    ip: IPv4Address = Field(..., alias="address")
    port: int = Field(..., ge=0, le=65535)

    @validator("protocol")
    def validate_protocol(cls, value: Protocol) -> Protocol:
        # pylint: disable=no-self-argument
        if value in TCP_IP_PROTOCOLS - MODBUS_TCP_IP_PROTOCOLS:
            return value
        raise ValueError(f"Expected {TCP_IP_PROTOCOLS - MODBUS_TCP_IP_PROTOCOLS}")

    @property
    def interface(self) -> tuple[IPv4Address, int]:
        return self.ip, self.port

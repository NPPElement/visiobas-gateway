from abc import ABC
from ipaddress import IPv4Address
from typing import Optional

from ..models import BACnetDeviceObj, Protocol
from ..utils import get_file_logger


class BaseDevice(ABC):
    def __init__(self, device_obj: BACnetDeviceObj, gateway):
        self._gateway = gateway
        self._device_obj = device_obj
        self._LOG = get_file_logger(name=__name__ + str(self.id))

    @property
    def id(self) -> int:
        """Device id."""
        return self._device_obj.id

    @property
    def address(self) -> Optional[IPv4Address]:
        return self._device_obj.property_list.address

    @property
    def port(self) -> Optional[int]:
        return self._device_obj.property_list.port

    @property
    def protocol(self) -> Protocol:
        return self._device_obj.property_list.protocol

    @property
    def timeout(self) -> float:
        return self._device_obj.timeout_sec
from abc import ABC
from ipaddress import IPv4Address
from typing import TYPE_CHECKING, Optional

from ..schemas import DeviceObj
from ..schemas.protocol import CAMERA_PROTOCOLS, POLLING_PROTOCOLS, Protocol
from ..utils import get_file_logger

if TYPE_CHECKING:
    from ..gateway_ import Gateway
else:
    Gateway = "Gateway"


class BaseDevice(ABC):
    """Base class for all devices."""

    def __init__(self, device_obj: DeviceObj, gateway: Gateway):
        self._gtw = gateway
        self._dev_obj = device_obj
        self._LOG = get_file_logger(name="_".join((__name__, str(self.device_id))))

    @property
    def device_id(self) -> int:
        """Device id."""
        return self._dev_obj.id

    @property
    def address(self) -> Optional[IPv4Address]:
        if hasattr(self._dev_obj.property_list, "address"):
            return self._dev_obj.property_list.address  # type: ignore
        return None

    @property
    def port(self) -> Optional[int]:
        if hasattr(self._dev_obj.property_list, "port"):
            return self._dev_obj.property_list.port  # type: ignore
        return None

    @property
    def protocol(self) -> Protocol:
        return self._dev_obj.property_list.protocol

    @property
    def timeout(self) -> float:
        return self._dev_obj.timeout_sec

    @property
    def is_camera(self) -> bool:
        return self.protocol in CAMERA_PROTOCOLS

    @property
    def is_polling_device(self) -> bool:
        return self.protocol in POLLING_PROTOCOLS

from abc import ABC
from typing import TYPE_CHECKING

from ..schemas import DeviceObj
from ..schemas.protocol import Protocol
from ..utils import get_file_logger

if TYPE_CHECKING:
    from ..gateway import Gateway
else:
    Gateway = "Gateway"


class BaseDevice(ABC):
    """Base class for all devices."""

    def __init__(self, device_obj: DeviceObj, gateway: Gateway):
        self._gateway = gateway
        self._device_obj = device_obj
        self._LOG = get_file_logger(name="_".join(("device", str(self.id))))

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}[{self._device_obj.device_id}, "
            f"{self._device_obj.property_list.protocol}]"
        )

    @property
    def id(self) -> int:
        """Device id."""
        return self._device_obj.object_id

    @property
    def protocol(self) -> Protocol:
        return self._device_obj.property_list.protocol

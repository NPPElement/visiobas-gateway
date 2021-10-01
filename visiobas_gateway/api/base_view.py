from typing import TYPE_CHECKING, Optional

from aiohttp.web_urldispatcher import View

from ..devices.base_polling_device import BasePollingDevice
from ..utils import get_file_logger

_LOG = get_file_logger(name=__name__)

if TYPE_CHECKING:
    from ..devices.base_device import BaseDevice
    from ..gateway import Gateway
    from ..schemas import BACnetObj
else:
    BaseDevice = "BaseDevice"
    Gateway = "Gateway"
    BACnetObj = "BACnetObj"


class BaseView(View):
    """Base class for all endpoints related with devices and their objects."""

    @property
    def gtw(self) -> Gateway:
        """
        Returns:
            Gateway instance.
        """
        return self.request.app["visiobas_gateway"]

    def get_device(self, device_id: int) -> Optional[BaseDevice]:
        """
        Args:
            device_id: Device identifier.

        Returns:
            Device instance if exists.
        """
        return self.gtw.get_device(dev_id=device_id)

    @staticmethod
    def get_obj(
        obj_id: int, obj_type_id: int, device: BasePollingDevice
    ) -> Optional[BACnetObj]:
        """
        Args:
            device: Device instance.
            obj_type_id: Object type identifier.
            obj_id: Object identifier.

        Returns:
            Object instance if exist.
        """
        if not isinstance(device, BasePollingDevice):
            raise ValueError(f"Device type must be polling. Got {type(device)}.")

        return device.get_object(obj_id=obj_id, obj_type_id=obj_type_id)

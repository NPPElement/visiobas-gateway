# from abc import abstractmethod
from typing import Any, Optional

from aiohttp.web_urldispatcher import View

from ..utils import get_file_logger

_LOG = get_file_logger(name=__name__)

# Aliases
VisioBASGatewayAlias = Any  # '..gateway_.VisioBASGateway'
DeviceAlias = Any  # Union['..devices.AsyncModbusDevice',]
ObjAlias = Any  # Union['..models.BACnetObj',]


class BaseView(View):
    """Base class for all endpoints related with devices and their objects."""

    @property
    def gtw(self) -> VisioBASGatewayAlias:
        """
        Returns:
            Gateway instance.
        """
        return self.request.app["gateway"]

    def get_device(self, dev_id: int) -> Optional[DeviceAlias]:
        """
        Args:
            dev_id: Device identifier.

        Returns:
            Device instance if exists.
        """
        return self.gtw.get_device(dev_id=dev_id)

    @staticmethod
    def get_obj(obj_id: int, obj_type_id: int, dev: DeviceAlias) -> Optional[ObjAlias]:
        """
        Args:
            dev: Device instance.
            obj_type_id: Object type identifier.
            obj_id: Object identifier.

        Returns:
            Object instance if exist.
        """
        return dev.get_object(obj_id=obj_id, obj_type_id=obj_type_id)

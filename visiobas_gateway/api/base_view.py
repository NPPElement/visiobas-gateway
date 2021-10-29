from typing import TYPE_CHECKING

import aiojobs  # type: ignore
from aiohttp.web_urldispatcher import View

from ..devices import BaseDevice, BasePollingDevice
from ..schemas import BACnetObj
from ..utils import get_file_logger

_LOG = get_file_logger(name=__name__)

if TYPE_CHECKING:
    from ..gateway import Gateway
else:
    Gateway = "Gateway"


class BaseView(View):
    """Base class for all endpoints related with devices and their objects."""

    @property
    def _gateway(self) -> Gateway:
        """
        Returns:
            Gateway instance.
        """
        return self.request.app["gateway"]

    @property
    def _scheduler(self) -> aiojobs.Scheduler:
        """
        Returns:
            Scheduler instance.
        """
        return self.request.app["scheduler"]

    def _get_device(self, device_id: int) -> BaseDevice:
        """
        Args:
            device_id: Device identifier.

        Returns:
            Device instance if exists.

        Raises:
            Exception: if device not found.
        """
        device = self._gateway.get_device(dev_id=device_id)
        if isinstance(device, BaseDevice):
            return device
        raise Exception(f"Device {device_id} not found.")

    def get_polling_device(self, device_id: int) -> BasePollingDevice:
        """
        Args:
            device_id: Device identifier.

        Returns:
            Device instance if exists.

        Raises:
            Exception: if device not subclass of `BasePollingDevice`.
        """
        device = self._get_device(device_id=device_id)
        if isinstance(device, BasePollingDevice):
            return device
        raise Exception(
            f"Device protocol must be polling. "
            f"Protocol of device {device.id} is {device.protocol}. It's not polling "
            f"protocol."
        )

    @staticmethod
    def get_obj(obj_id: int, obj_type_id: int, device: BasePollingDevice) -> BACnetObj:
        """
        Args:
            device: Device instance.
            obj_type_id: Object type identifier.
            obj_id: Object identifier.

        Returns:
            Object instance.

        Raises:
            Exception: if object not found.
        """
        obj = device.get_object(object_id=obj_id, object_type_id=obj_type_id)

        if isinstance(obj, BACnetObj):
            return obj

        raise Exception(
            f"Object ({obj_type_id}, {obj_id}) not found in device {device.id}."
        )

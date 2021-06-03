from typing import Union, Optional, Any

from aiohttp.web_exceptions import HTTPNotFound
from aiohttp.web_urldispatcher import View

from ..utils import get_file_logger

_LOG = get_file_logger(name=__name__)

# Aliases
VisioBASGatewayAlias = Any  # '..gateway_.VisioBASGateway'
DeviceAlias = Any  # Union['..devices.AsyncModbusDevice',]
ObjAlias = Any  # Union['..models.BACnetObj',]


class BaseView(View):
    @property
    def gtw(self) -> VisioBASGatewayAlias:
        """
        Returns:
            Gateway instance.
        """
        return self.request.app['gateway']

    def get_device(self, dev_id: int) -> Optional[DeviceAlias]:
        """
        Args:
            dev_id: Device identifier.

        Returns:
            Device instance is exists.
        """
        try:
            return self.gtw.get_device(dev_id=dev_id, gtw=self.gtw)
        except (ValueError, AttributeError, Exception) as e:
            _LOG.warning('Exception',
                         extra={'gateway': self.gtw, 'device_id': dev_id, 'exc': e, })
            raise HTTPNotFound(reason=f'Exception: {e}\nTraceback: {e.__traceback__}')

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
        try:
            return dev.get_obj(obj_id=obj_id, obj_type_id=obj_type_id, dev=dev)
        except (ValueError, AttributeError, Exception) as e:
            _LOG.warning('Exception', extra={'device_id': dev.id, 'exc': e, })
            raise HTTPNotFound(reason=f'Exception: {e}\nTraceback: {e.__traceback__}')

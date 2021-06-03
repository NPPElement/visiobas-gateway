from typing import Union, Optional, Any

from aiohttp.web_exceptions import HTTPNotFound
from aiohttp.web_urldispatcher import View

from .mixins import GetDevObjMixin
from ..utils import get_file_logger

_LOG = get_file_logger(name=__name__)

# Aliases
VisioBASGatewayAlias = Any  # '..gateway_.VisioBASGateway'
DeviceAlias = Any  # Union['..devices.AsyncModbusDevice',]
ObjAlias = Any  # Union['..models.BACnetObj',]


class BaseView(View, GetDevObjMixin):
    @property
    def gateway(self) -> VisioBASGatewayAlias:
        return self.request.app['gateway']

    def get_device(self, dev_id: int) -> Optional[DeviceAlias]:
        """
        Args:
            dev_id: Device identifier.

        Returns:
            Device instance.
        """
        try:
            return GetDevObjMixin.get_device(dev_id=dev_id, gtw=self.gateway)
        except (ValueError, AttributeError, Exception) as e:
            _LOG.warning('Exception', extra={'gateway': self.gateway, 'device_id': dev_id,
                                             'exc': e, })
            raise HTTPNotFound(reason=f'Exception: {e}\nTraceback: {e.__traceback__}')

        # except ValueError as e:
        #     raise HTTPNotFound(reason=str(e.args))
        # except AttributeError as e:
        #     _LOG.error(f'Error: {e}',
        #                exc_info=True
        #                )
        #     raise HTTPNotFound(
        #         reason=f'Invalid gateway {self.gateway} {type(self.gateway)}')

    @staticmethod
    def get_obj(obj_id: int, obj_type_id: int, device: DeviceAlias) -> ObjAlias:
        """
        Args:
            device: Device instance.
            obj_type_id: Object type identifier.
            obj_id: Object identifier.

        Returns:
            Object instance.
        """
        try:
            return GetDevObjMixin.get_obj(obj_id=obj_id, obj_type_id=obj_type_id,
                                          device=device)
        except (ValueError, AttributeError, Exception) as e:
            _LOG.warning('Exception',
                         extra={  # 'gateway': self.gateway,
                             'device_id': device.id, 'exc': e, })
            raise HTTPNotFound(reason=f'Exception: {e}\nTraceback: {e.__traceback__}')

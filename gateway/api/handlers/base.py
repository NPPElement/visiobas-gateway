from logging import getLogger

from aiohttp.web_exceptions import HTTPNotFound
from aiohttp.web_urldispatcher import View

from ..mixins import DevObjMixin

_log = getLogger(__name__)


class BaseView(View, DevObjMixin):
    @property
    def gateway(self):  # -> VisioGateway
        return self.request.app['gateway']

    def get_device(self, dev_id: int):  # ->  Device(Thread)
        # _log.critical(BaseView.__mro__)
        try:
            DevObjMixin.get_device(dev_id=dev_id,
                                   gateway=self.gateway
                                   )
        except ValueError as e:
            raise HTTPNotFound(reason=str(e.args))
        except AttributeError as e:
            _log.error(f'Error: {e}',
                       exc_info=True
                       )
            raise HTTPNotFound(
                reason=f'Invalid gateway {self.gateway} {type(self.gateway)}')

    @staticmethod
    def get_obj(device, obj_type: int, obj_id: int):  # -> ProtocolObj
        """Returns protocol's object."""
        try:
            DevObjMixin.get_obj(device=device,
                                obj_type=obj_type,
                                obj_id=obj_id
                                )
        except ValueError as e:
            raise HTTPNotFound(reason=str(e.args))
        except AttributeError as e:
            _log.error(f'Error: {e}',
                       exc_info=True
                       )
            raise HTTPNotFound(reason=f'Invalid device {device}:{type(device)}')

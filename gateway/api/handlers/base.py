from aiohttp.web_exceptions import HTTPNotFound
from aiohttp.web_urldispatcher import View

from gateway.utils import get_file_logger

_log = get_file_logger(logger_name=__name__)


class BaseView(View):
    @property
    def gateway(self):  # -> VisioGateway
        return self.request.app['gateway']

    def get_device(self, dev_id: int):  # ->  Device(Thread)
        """Returns device's thread (for interactions with object)."""
        try:
            for con in self.gateway.connectors.values():
                if dev_id in con.polling_devices:
                    return con.polling_devices[dev_id]
            raise HTTPNotFound(reason=f'Device id {dev_id} not polling.')
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
            for obj in device.objects:
                if obj.type.id == obj_type and obj.id == obj_id:
                    return obj
            raise HTTPNotFound(reason=f'Object type {obj_type} id:{obj_id} '
                                      f'not polling at {device}.')
        except AttributeError as e:
            _log.error(f'Error: {e}',
                       exc_info=True
                       )
            raise HTTPNotFound(reason=f'Invalid device {device}:{type(device)}')

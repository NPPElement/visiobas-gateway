from aiohttp.web_exceptions import HTTPNotFound
from aiohttp.web_urldispatcher import View

from logs import get_file_logger

_log = get_file_logger(logger_name=__name__)


class BaseView(View):
    @property
    def gateway(self):  # -> VisioGateway
        return self.request.app['gateway']

    @property
    def device_id(self) -> int:
        return int(self.request.match_info.get('device_id'))

    @property
    def object_type(self) -> int:
        return int(self.request.match_info.get('params').get('object_type'))

    @property
    def object_id(self) -> int:
        return int(self.request.match_info.get('params').get('object_id'))

    @property
    def property_(self) -> int:
        return int(self.request.match_info.get('params').get('property'))

    def get_device(self):  # ->  Device
        """Returns device's thread (for interactions with object)."""
        try:
            for con in self.gateway.connectors.values():
                if self.device_id in con.polling_devices:
                    return con.polling_devices[self.device_id]
            raise HTTPNotFound(reason=f'Device id {self.device_id} not polling.')
        except AttributeError as e:
            _log.error(f'Error: {e}',
                       exc_info=True
                       )
            raise HTTPNotFound(reason=f'Invalid gateway {self.gateway} {type(self.gateway)}')

    def get_obj(self, device):  # -> ModbusObj
        """Returns protocol's object."""
        try:
            for obj in device.objects:
                if obj.type.id == self.object_type and obj.id == self.object_id:
                    return obj
            raise HTTPNotFound(reason=f'Object type {self.object_type} id:{self.object_id} '
                                      f'not polling at {device}.')
        except AttributeError as e:
            _log.error(f'Error: {e}',
                       exc_info=True
                       )
            raise HTTPNotFound(reason=f'Invalid device {device}:{type(device)}')

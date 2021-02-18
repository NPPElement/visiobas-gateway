from http import HTTPStatus

from aiohttp.web_response import json_response
from aiohttp_apispec import docs

from gateway.api.handlers import ModbusMixin
from logs import get_file_logger

_log = get_file_logger(logger_name=__name__)


class ModbusPropertyView(ModbusMixin):
    URL_PATH = (r'/api/property/{device_id:\d+}/{object_type:\d+}/'
                r'{object_id:\d+}/{property:\d+}')

    @property
    def device_id(self) -> int:
        return int(self.request.match_info.get('device_id'))

    @property
    def object_type(self) -> int:
        return int(self.request.match_info.get('object_type'))

    @property
    def object_id(self) -> int:
        return int(self.request.match_info.get('object_id'))

    @property
    def property_(self) -> int:
        return int(self.request.match_info.get('property'))

    @docs(summary='Read property from object of device.')
    async def get(self):
        device = self.get_device(dev_id=self.device_id)
        obj = self.get_obj(device=device, obj_type=self.object_type, obj_id=self.object_id)

        value = self._modbus_read(obj=obj,
                                  device=device
                                  )
        return json_response({'value': value},
                             status=HTTPStatus.OK.value
                             )

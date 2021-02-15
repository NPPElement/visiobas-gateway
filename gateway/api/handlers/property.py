from http import HTTPStatus

from aiohttp.web_response import json_response
from aiohttp_apispec import docs

from .base_modbus import BaseModbusView


class ModbusPropertyView(BaseModbusView):
    URL_PATH = (r'/api/property/{device_id:\d+}/{object_type:\d+}/'
                r'{object_id:\d+}/{property:\d+}')

    @docs(summary='Read property from object of device.')
    async def get(self):
        device = self.get_device()
        obj = self.get_obj(device=device)

        value = self._modbus_read(obj=obj,
                                  device=device
                                  )
        return json_response({'value': value},
                             status=HTTPStatus.OK
                             )

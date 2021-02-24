from http import HTTPStatus
from logging import getLogger

from aiohttp.web_response import json_response
from aiohttp_apispec import docs, response_schema

from ...handlers import ModbusRWMixin, BaseView
from ...schema import JsonRPCPostResponseSchema, WriteResultSchema

_log = getLogger(__name__)


class ModbusPropertyView(BaseView, ModbusRWMixin):
    URL_PATH = (r'/api/v1/property/{device_id:\d+}/{object_type:\d+}/'
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

    @docs(summary='Read property from device object.')
    @response_schema(schema=WriteResultSchema, code=200)
    async def get(self):
        device = self.get_device(dev_id=self.device_id)
        obj = self.get_obj(device=device, obj_type=self.object_type, obj_id=self.object_id)

        value = self.read_modbus(obj=obj,
                                 device=device
                                 )
        return json_response({'value': value},
                             status=HTTPStatus.OK.value
                             )

    @docs(summary='Write property to device object with check.')
    @response_schema(schema=JsonRPCPostResponseSchema, code=HTTPStatus.OK.value)
    async def post(self):
        device = self.get_device(dev_id=self.device_id)
        obj = self.get_obj(device=device, obj_type=self.object_type, obj_id=self.object_id)

        body = await self.request.json()

        value = body.get('value')
        property_ = body.get('property')

        if property_ != 85:
            return json_response({'success': False,
                                  'msg': 'For now, only the presentValue(85) '
                                         'property is supported.'
                                  },
                                 status=HTTPStatus.NOT_IMPLEMENTED.value
                                 )

        self.write_modbus(value=value,
                          obj=obj,
                          device=device
                          )
        rvalue = self.read_modbus(obj=obj,
                                  device=device
                                  )
        if value == rvalue:
            return json_response({'success': True},
                                 status=HTTPStatus.OK.value
                                 )
        else:
            return json_response({'success': False,
                                  'msg': 'The read value does not match the written one. '
                                         f'Written: {value} Read: {rvalue}'
                                  },
                                 status=HTTPStatus.BAD_GATEWAY.value
                                 )

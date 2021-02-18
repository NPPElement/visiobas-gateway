from http import HTTPStatus

from aiohttp.web_exceptions import HTTPBadGateway
from aiohttp.web_response import json_response
from aiohttp_apispec import docs, request_schema, response_schema

from gateway.api.handlers.mixins import ModbusMixin

from gateway.api.schema import JsonRPCSchema, JsonRPCPostResponseSchema
from logs import get_file_logger

_log = get_file_logger(logger_name=__name__)


class JsonRPCView(ModbusMixin):
    URL_PATH = r'/json-rpc'

    @docs(summary='Device control with writing control.')
    @request_schema(JsonRPCSchema())
    @response_schema(JsonRPCPostResponseSchema, code=HTTPStatus.OK.value)
    async def post(self):
        body = await self.request.json()
        dev_id = int(body.get('params').get('device_id'))
        obj_type = int(body.get('params').get('object_type'))
        obj_id = int(body.get('params').get('object_id'))
        value_str = body.get('params').get('value')
        value = float(value_str) if '.' in value_str else int(value_str)

        device = self.get_device(dev_id=dev_id)
        obj = self.get_obj(device=device, obj_type=obj_type, obj_id=obj_id)

        self._modbus_write(value=value,
                           obj=obj,
                           device=device
                           )
        rvalue = self._modbus_read(obj=obj,
                                   device=device
                                   )
        if value == rvalue:
            return json_response({'success': True},
                                 status=HTTPStatus.OK.value
                                 )
        else:
            raise HTTPBadGateway

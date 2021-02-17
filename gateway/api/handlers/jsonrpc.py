from http import HTTPStatus

from aiohttp.web_exceptions import HTTPBadGateway
from aiohttp.web_response import json_response
from aiohttp_apispec import docs, request_schema, response_schema

from gateway.api.schema import JsonRPCSchema, JsonRPCPostResponseSchema
from logs import get_file_logger
from .base_modbus import BaseModbusView

_log = get_file_logger(logger_name=__name__)


class JsonRPCView(BaseModbusView):
    URL_PATH = r'/json-rpc'

    # TODO

    @property
    def priority(self):
        return int(self.request.match_info.get('params').get('priority'))

    @property
    def value(self) -> int:
        return int(self.request.match_info.get('params').get('value'))

    @docs(summary='Device control with writing control.')
    @request_schema(JsonRPCSchema())
    @response_schema(JsonRPCPostResponseSchema, code=HTTPStatus.OK.value)
    async def post(self):
        device = self.get_device()
        obj = self.get_obj(device=device)

        self._modbus_write(value=self.value,
                           obj=obj,
                           device=device
                           )
        value = self._modbus_read(obj=obj,
                                  device=device
                                  )
        if value == self.value:
            return json_response({'success': True},
                                 status=HTTPStatus.OK.value
                                 )
        else:
            raise HTTPBadGateway

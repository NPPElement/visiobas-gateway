from http import HTTPStatus
from logging import getLogger

from aiohttp.web_exceptions import HTTPBadGateway
from aiohttp.web_response import json_response
from aiohttp_apispec import docs, request_schema, response_schema

from gateway.models import ObjProperty
from ...handlers import BaseView
from ...mixins import ReadWriteMixin
from ...schema import JsonRPCSchema, JsonRPCPostResponseSchema

_log = getLogger(__name__)


class JsonRPCView(BaseView, ReadWriteMixin):
    URL_PATH = r'/json-rpc'

    @docs(summary='Write property to device object with check.')
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
        try:
            _values_equal = self.write_with_check(value=value,
                                                  prop=ObjProperty.presentValue,
                                                  priority=11,  # todo: sure?
                                                  obj=obj,
                                                  device=device
                                                  )
            if _values_equal:
                return json_response({'success': True},
                                     status=HTTPStatus.OK.value
                                     )
            else:
                return json_response({'success': False,
                                      'msg': 'The read value ins\'t equal to the written value.'
                                      # f'Written: {value} Read: {rvalue}'
                                      },
                                     status=HTTPStatus.BAD_GATEWAY.value
                                     )
        except Exception as e:
            return HTTPBadGateway(reason=str(e))

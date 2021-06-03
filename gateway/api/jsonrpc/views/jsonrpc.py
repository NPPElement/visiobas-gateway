from http import HTTPStatus

from aiohttp.web_exceptions import HTTPBadGateway
from aiohttp.web_response import json_response
from aiohttp_apispec import docs, request_schema, response_schema

from ...base_view import BaseView
from ...mixins import ReadWriteMixin
from ...schema import JsonRPCSchema, JsonRPCPostResponseSchema
from ....models import ObjProperty
from ....utils import get_file_logger

_LOG = get_file_logger(name=__name__)


class JsonRPCView(BaseView, ReadWriteMixin):
    URL_PATH = r'/json-rpc'

    @docs(summary='Write property to object with check.')
    @request_schema(JsonRPCSchema())
    @response_schema(JsonRPCPostResponseSchema, code=HTTPStatus.OK.value)
    async def post(self):
        body = await self.request.json()
        dev_id = int(body.get('params').get('device_id'))
        obj_type_id = int(body.get('params').get('object_type'))
        obj_id = int(body.get('params').get('object_id'))
        value_str = body.get('params').get('value')
        value = float(value_str) if '.' in value_str else int(value_str)

        dev = self.get_device(dev_id=dev_id)
        obj = self.get_obj(dev=dev, obj_type_id=obj_type_id, obj_id=obj_id)
        try:
            _values_equal = await self.write_with_check(value=value,
                                                        prop=ObjProperty.presentValue,
                                                        priority=self.gtw.api_priority,
                                                        obj=obj, device=dev)
            if _values_equal:
                _LOG.debug('Read and written values are consistent',
                           extra={'device_id': dev_id, 'object_id': obj_id,
                                  obj_type_id: obj_type_id, 'value': value, })
                return json_response({'success': True}, status=HTTPStatus.OK.value)
            else:
                _LOG.warning('Read and written values are not consistent.',
                             extra={'device_id': dev_id, 'object_id': obj_id,
                                    obj_type_id: obj_type_id, 'value': value, })
                return json_response({
                    'success': False,
                    'msg': 'Read and written values are not consistent.'
                },
                    status=HTTPStatus.BAD_GATEWAY.value
                )
        except Exception as e:
            return HTTPBadGateway(reason=f'Exception: {e}\nTraceback: {e.__traceback__}')

# from http import HTTPStatus
# from logging import getLogger
#
# from aiohttp.web_exceptions import HTTPBadGateway
# from aiohttp.web_response import json_response
# from aiohttp_apispec import docs, response_schema
#
# from api.base import BaseView
# from api.mixins import ReadWriteMixin
# from api.schema import JsonRPCPostResponseSchema, ReadResultSchema
# from models import ObjProperty
#
# _log = getLogger(__name__)
#
#
# class PropertyView(BaseView, ReadWriteMixin):
#     URL_PATH = (r'/api/v1/property/{device_id:\d+}/{object_type:\d+}/'
#                 r'{object_id:\d+}/{property:\d+}')
#
#     @property
#     def device_id(self) -> int:
#         return int(self.request.match_info.get('device_id'))
#
#     @property
#     def object_type(self) -> int:
#         return int(self.request.match_info.get('object_type'))
#
#     @property
#     def object_id(self) -> int:
#         return int(self.request.match_info.get('object_id'))
#
#     @property
#     def property_(self) -> int:
#         return int(self.request.match_info.get('property'))
#
#     @docs(summary='Read property from device object.')
#     @response_schema(schema=ReadResultSchema, code=200)
#     async def get(self):
#         device = self.get_device(dev_id=self.device_id)
#         obj = self.get_obj(
#         device=device, obj_type=self.object_type, obj_id=self.object_id
#         )
#         try:
#             value = self.read(prop=ObjProperty.presentValue,
#                               obj=obj,
#                               device=device
#                               )
#             return json_response({'value': value},
#                                  status=HTTPStatus.OK.value
#                                  )
#         except Exception as e:
#             return HTTPBadGateway(reason=str(e))
#
#     @docs(summary='Write property to device object with check.')
#     @response_schema(schema=JsonRPCPostResponseSchema, code=HTTPStatus.OK.value)
#     async def post(self):
#         device = self.get_device(dev_id=self.device_id)
#         obj = self.get_obj(
#               device=device, obj_type=self.object_type, obj_id=self.object_id
#         )
#
#         body = await self.request.json()
#         try:
#             value = body['value']
#             _values_equal = self.write_with_check(value=value,
#                                                   prop=ObjProperty.presentValue,
#                                                   priority=11,  # todo: sure?
#                                                   obj=obj,
#                                                   device=device
#                                                   )
#             if _values_equal:
#                 return json_response({'success': True},
#                                      status=HTTPStatus.OK.value
#                                      )
#             else:
#                 return json_response(
#                 {'success': False,
#                           'msg': 'The read value ins\'t equal to the written value.'
#                                    # f'Written: {value} Read: {rvalue}'
#                                   },
#                                 status=HTTPStatus.BAD_GATEWAY.value
#                                  )
#         except Exception as e:
#             return HTTPBadGateway(reason=str(e))
#
#
# if __name__ == '__main__':
#     print(PropertyView.__mro__)

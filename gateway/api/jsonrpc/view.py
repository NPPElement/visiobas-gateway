from aiohttp_cors import CorsViewMixin, ResourceOptions
from aiohttp_jsonrpc import handler

from ..base_view import BaseView
from ..mixins import ReadWriteMixin
from ...models import ObjProperty
from ...utils import get_file_logger

_LOG = get_file_logger(__name__)


class JsonRPCView(handler.JSONRPCView, ReadWriteMixin, BaseView, CorsViewMixin):
    URL_PATH = r'/json-rpc'

    cors_config = {
        "*": ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods='*'
        )
    }

    async def rpc_writeSetPoint(self, *args, **kwargs):
        dev_id = int(kwargs.get('device_id'))
        obj_type_id = int(kwargs.get('object_type'))
        obj_id = int(kwargs.get('object_id'))
        priority = int(kwargs.get('priority'))
        value = float(kwargs.get('value'))
        # value = float(value_str) if '.' in value_str else int(value_str)

        _LOG.debug('Call params', extra={'args_': args, 'kwargs_': kwargs, })
        dev = self.get_device(dev_id=dev_id)
        if dev is None:
            raise Exception('Device not found')

        obj = self.get_obj(dev=dev, obj_type_id=obj_type_id, obj_id=obj_id)
        if obj is None:
            raise Exception('Object not found')

        is_consistent = await self.write_with_check(
            value=value, prop=ObjProperty.presentValue, priority=priority,
            obj=obj, device=dev)

        return is_consistent

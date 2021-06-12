from aiohttp_jsonrpc import handler

from ..base_view import BaseView
from ..mixins import ReadWriteMixin
from ...models import ObjProperty


class JsonRPCView(handler.JSONRPCView, ReadWriteMixin, BaseView):
    URL_PATH = r'/json-rpc'

    def rpc_write_set_point(self, *args, **kwargs):
        dev_id = int(kwargs.get('params').get('device_id'))
        obj_type_id = int(kwargs.get('params').get('object_type'))
        obj_id = int(kwargs.get('params').get('object_id'))
        priority = int(kwargs.get('params').get('priority'))
        value = float(kwargs.get('params').get('value'))
        # value = float(value_str) if '.' in value_str else int(value_str)

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

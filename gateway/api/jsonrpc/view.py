from aiohttp_cors import CorsViewMixin, ResourceOptions
from aiohttp_jsonrpc import handler

from ...models import ObjProperty
from ...utils import get_file_logger
from ..base_view import BaseView

_LOG = get_file_logger(__name__)


class JsonRPCView(handler.JSONRPCView, BaseView, CorsViewMixin):
    URL_PATH = r"/json-rpc"

    cors_config = {
        "*": ResourceOptions(
            allow_credentials=False,
            expose_headers="*",
            allow_headers="*",
            allow_methods=[
                "POST",
            ],
        )
    }

    async def rpc_writeSetPoint(self, *args, **kwargs):
        _LOG.debug(
            "Call params",
            extra={
                "args_": args,
                "kwargs_": kwargs,
            },
        )

        dev_id = int(kwargs.get("device_id"))
        obj_type_id = int(kwargs.get("object_type"))
        obj_id = int(kwargs.get("object_id"))
        priority = int(kwargs.get("priority"))
        value = float(kwargs.get("value"))

        if value.is_integer():
            value = int(value)

        dev = self.get_device(dev_id=dev_id)
        if dev is None or not dev.is_polling_device:
            raise Exception("Device not found")

        obj = self.get_obj(dev=dev, obj_type_id=obj_type_id, obj_id=obj_id)
        if obj is None:
            raise Exception("Object not found")

        is_consistent = await dev.write_with_check(
            value=value,
            prop=ObjProperty.presentValue,
            priority=priority,
            obj=obj,
            device=dev,
        )

        return {"success": is_consistent}

    async def rpc_ptz(self, *args, **kwargs):
        _LOG.debug(
            "Call params",
            extra={
                "args_": args,
                "kwargs_": kwargs,
            },
        )

        dev_id = int(kwargs.get("device_id"))
        dev = self.get_device(dev_id=dev_id)

        if dev is None or not dev.is_camera:
            raise Exception("Device not found")

        dev.ptz(**kwargs)  # add check

        return {"success": "not checking now"}

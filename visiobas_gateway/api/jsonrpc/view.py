from typing import TYPE_CHECKING, Any

from aiohttp_cors import CorsViewMixin, ResourceOptions  # type: ignore
from aiohttp_jsonrpc import handler  # type: ignore

from ...schemas import ObjProperty
from ...utils import get_file_logger
from ..base_view import BaseView

_LOG = get_file_logger(name=__name__)


if TYPE_CHECKING:
    from ...devices.base_polling_device import BasePollingDevice
    from ...devices.sunapi import SUNAPIDevice
else:
    BasePollingDevice = "BasePollingDevice"
    SUNAPIDevice = "SUNAPIDevice"


class JsonRPCView(handler.JSONRPCView, BaseView, CorsViewMixin):
    """JSON-RPC Endpoint."""

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

    async def rpc_writeSetPoint(self, *args: str, **kwargs: str) -> dict:
        _LOG.debug(
            "Call params",
            extra={
                "args_": args,
                "kwargs_": kwargs,
            },
        )
        device_id = int(kwargs["device_id"])
        obj_type_id = int(kwargs["object_type"])
        obj_id = int(kwargs["object_id"])
        priority = int(kwargs["priority"])
        value = float(kwargs["value"])
        if value.is_integer():
            value = int(value)

        device = self.get_device(device_id=device_id)
        if device is None:
            raise Exception("Device not found")
        if not isinstance(device, BasePollingDevice):
            raise Exception("Device protocol is not polling.")

        obj = self.get_obj(device=device, obj_type_id=obj_type_id, obj_id=obj_id)
        if obj is None:
            raise Exception("Object not found")

        is_consistent = await device.write_with_check(
            value=value,
            prop=ObjProperty.PRESENT_VALUE,
            priority=priority,
            obj=obj,
            device=device,
        )
        return {"success": is_consistent}

    async def rpc_ptz(self, *args: Any, **kwargs: Any) -> dict:
        _LOG.debug(
            "Call params",
            extra={
                "args_": args,
                "kwargs_": kwargs,
            },
        )

        device_id = int(kwargs["device_id"])
        device = self.get_device(device_id=device_id)

        if device is None:
            raise Exception("Device not found.")

        if not isinstance(device, SUNAPIDevice):
            raise Exception("Device is not SunAPI camera.")

        device.ptz(**kwargs)  # add check

        return {"success": "WARNING! Success check is not implemented now!"}

from typing import Any

from aiohttp_cors import CorsViewMixin, ResourceOptions  # type: ignore
from aiohttp_jsonrpc import handler  # type: ignore

from visiobas_gateway.devices.bacnet import BACnetDevice

from ...devices.sunapi import SUNAPIDevice
from ...schemas import ObjProperty, ObjType, Priority
from ...utils import get_file_logger
from ..base_view import BaseView

_LOG = get_file_logger(name=__name__)


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

    async def rpc_resetSetPoint(self, *args: Any, **kwargs: Any) -> dict:
        # pylint: disable=unused-argument
        device_id = int(kwargs["device_id"])
        obj_type = ObjType(int(kwargs["object_type"]))
        obj_id = int(kwargs["object_id"])
        priority = Priority(int(kwargs["priority"]))

        device = self.get_polling_device(device_id=device_id)
        if not isinstance(device, BACnetDevice):
            raise Exception(
                "Only BACnet objects has priorityArray. "
                "So only BACnet devices can reset priorityArray. "
                f"This device using {device.protocol} protocol."
            )
        obj = self.get_obj(device=device, obj_type_id=obj_type.value, obj_id=obj_id)
        obj = await device.write_with_check(
            value="null",
            prop=ObjProperty.PRESENT_VALUE,
            priority=priority.value,
            obj=obj,
            device=device,
        )
        return {"success": obj.priority_array[priority.value] is None}

    async def rpc_writeSetPoint(self, *args: Any, **kwargs: Any) -> dict:
        # pylint: disable=unused-argument
        device_id = int(kwargs["device_id"])
        obj_type = ObjType(int(kwargs["object_type"]))
        obj_id = int(kwargs["object_id"])
        priority = Priority(int(kwargs["priority"]))
        value = float(kwargs["value"])
        if value.is_integer():
            value = int(value)

        device = self.get_polling_device(device_id=device_id)
        obj = self.get_obj(device=device, obj_type_id=obj_type.value, obj_id=obj_id)
        obj = await device.write_with_check(
            value=value,
            prop=ObjProperty.PRESENT_VALUE,
            priority=priority.value,
            obj=obj,
            device=device,
        )
        await self._scheduler.spawn(self._gateway.send_objects(objs=[obj]))

        is_consistent = value == obj.present_value

        if is_consistent:
            return {"success": is_consistent}
        return {
            "success": is_consistent,
            "msg": f"The written value ({value}) does not match "
            "the "
            f"read ({obj.present_value}).",
        }

    async def rpc_ptz(self, *args: Any, **kwargs: Any) -> dict:
        _LOG.debug(
            "Call params",
            extra={
                "args_": args,
                "kwargs_": kwargs,
            },
        )

        device_id = int(kwargs["device_id"])
        device = self._get_device(device_id=device_id)

        if not isinstance(device, SUNAPIDevice):
            raise Exception("Device is not SunAPI camera.")

        device.ptz(**kwargs)  # add check

        return {"success": "WARNING! Success check is not implemented now!"}

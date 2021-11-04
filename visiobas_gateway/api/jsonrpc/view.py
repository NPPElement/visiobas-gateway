from typing import Any

from aiohttp_cors import CorsViewMixin, ResourceOptions  # type: ignore
from aiohttp_jsonrpc import handler  # type: ignore

from ...devices import BACnetDevice
from ...schemas import ObjProperty
from ...utils import get_file_logger, log_exceptions
from ..base_view import BaseView
from .schemas import JsonRPCSetPointParams

_LOG = get_file_logger(name=__name__)

_AIOHTTP_JSON_RPC_LOGGERS = [
    "aiohttp_jsonrpc.handler",
]
for aiohttp_logger in [*_AIOHTTP_JSON_RPC_LOGGERS]:
    get_file_logger(aiohttp_logger)


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

    @log_exceptions(logger=_LOG)
    async def rpc_resetSetPoint(self, *args: Any, **kwargs: Any) -> dict:
        """Resets priorityArray value in BACnet device."""
        params = JsonRPCSetPointParams(**kwargs)
        _LOG.debug(
            "Call params", extra={"args_": args, "kwargs_": kwargs, "params": params}
        )

        device = self.get_polling_device(device_id=params.device_id)
        if not isinstance(device, BACnetDevice):
            raise Exception(
                "Only BACnet objects has priorityArray. "
                "So only BACnet devices can reset priorityArray. "
                f"This device using {device.protocol} protocol."
            )
        obj = self.get_obj(
            device=device, obj_type_id=params.object_type.value, obj_id=params.object_id
        )
        output_obj, input_obj = await device.write_with_check(
            value="null",
            prop=ObjProperty.PRESENT_VALUE,
            priority=params.priority.value,
            output_obj=obj,
            device=device,
        )
        await self._scheduler.spawn(
            self._gateway.send_objects(objs=[obj for obj in (output_obj, input_obj) if obj])
        )
        success = output_obj.priority_array[params.priority.value - 1] is None
        if success:
            return {"success": success}
        return {
            "success": success,
            "msg": "Priority not `null`",
            "debug": {
                "priority": params.priority.value,
                "priorityArray": output_obj.priority_array,
            },
        }

    @log_exceptions(logger=_LOG)
    async def rpc_writeSetPoint(self, *args: Any, **kwargs: Any) -> dict:
        """Writes value to any polling device."""
        params = JsonRPCSetPointParams(**kwargs)
        _LOG.debug(
            "Call params", extra={"args_": args, "kwargs_": kwargs, "params": params}
        )
        device = self.get_polling_device(device_id=params.device_id)
        obj = self.get_obj(
            device=device, obj_type_id=params.object_type.value, obj_id=params.object_id
        )
        output_obj, input_obj = await device.write_with_check(
            value=params.value,
            prop=ObjProperty.PRESENT_VALUE,
            priority=params.priority.value,
            output_obj=obj,
            device=device,
        )
        await self._scheduler.spawn(
            self._gateway.send_objects(objs=[obj for obj in (output_obj, input_obj) if obj])
        )
        success = params.value == output_obj.present_value
        if success:
            return {"success": success}
        return {
            "success": success,
            "msg": "The written value does not match the read.",
            "debug": {
                "written_value": params.value,
                "read_value": output_obj.present_value,
            },
        }

    # async def rpc_ptz(self, *args: Any, **kwargs: Any) -> dict:
    #     _LOG.debug(
    #         "Call params",
    #         extra={
    #             "args_": args,
    #             "kwargs_": kwargs,
    #         },
    #     )
    #
    #     device_id = int(kwargs["device_id"])
    #     device = self._get_device(device_id=device_id)
    #
    #     if not isinstance(device, SUNAPIDevice):
    #         raise Exception("Device is not SunAPI camera.")
    #
    #     device.ptz(**kwargs)  # add check
    #
    #     return {"success": "WARNING! Success check is not implemented now!"}

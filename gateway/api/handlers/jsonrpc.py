from aiohttp.web_exceptions import HTTPNotFound, HTTPBadGateway
from aiohttp.web_response import json_response
from aiohttp_apispec import docs, request_schema

from .base import BaseView
from gateway.api.schema import JsonRPCSchema
from gateway.connectors.modbus import ModbusDevice
from gateway.models.modbus import ModbusObj


class JsonRPCView(BaseView):
    URL_PATH = r'/json-rpc'

    @property
    def device_id(self) -> int:
        return int(self.request.match_info.get('device_id'))

    @property
    def object_type(self) -> int:
        return int(self.request.match_info.get('object_type'))

    @property
    def object_id(self) -> int:
        return int(self.request.match_info.get('object_id'))

    @property
    def property_(self) -> int:
        return int(self.request.match_info.get('property'))

    @property
    def value(self) -> int:
        return int(self.request.match_info.get('value'))

    def get_device(self):  # ->  Device
        """Returns device's thread (for interactions with object)."""
        for con in self.gateway.connectors:
            if self.device_id in con.polling_devices:
                return con.polling_devices[self.device_id]
        raise HTTPNotFound(reason=f'Device id {self.device_id} not polling.')

    def get_obj(self, device):  # -> ModbusObj
        """Returns protocol's object."""
        for obj in device.objects:
            if obj.type.id == self.object_type and obj.id == self.object_id:
                return obj
        raise HTTPNotFound(reason=f'Object type:{self.object_type} id:{self.object_id} '
                                  f'not polling at {device}.')

    def write(self, obj: ModbusObj, device: ModbusDevice) -> bool:
        """
        :param obj:
        :param device:
        :return: is write requests successful
        """
        if not isinstance(device, ModbusDevice):
            raise HTTPBadGateway

        try:
            device.write(cmd_code=obj.properties.func_write,
                         reg_address=obj.properties.address,
                         values=self.value
                         )
            return True
        except Exception:
            return False

    def read(self, obj: ModbusObj, device: ModbusDevice) -> bool:
        """
        :param obj:
        :param device:
        :return: is read value equal value in request
        """
        if not isinstance(device, ModbusDevice):
            raise HTTPBadGateway

        try:
            rr = device.read(cmd_code=obj.properties.func_read,
                             reg_address=obj.properties.address,
                             quantity=obj.properties.quantity
                             )
            if obj.properties.quantity == 1:
                value = rr.pop()
            else:
                raise NotImplementedError

            return value == self.value
        except:
            return False

    @docs(summary='Device control with writing control.')
    @request_schema(JsonRPCSchema())
    # @response_schema()
    async def post(self):
        device = self.get_device()
        obj = self.get_obj(device=device)

        is_write_successful = self.write(obj=obj,
                                         device=device
                                         )
        is_requested_value = self.read(obj=obj,
                                       device=device
                                       )
        return json_response()

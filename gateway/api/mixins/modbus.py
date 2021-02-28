from logging import getLogger
from typing import Any

from aiohttp.web_exceptions import HTTPBadGateway

from gateway.connectors import ModbusDevice
from gateway.models import ModbusObj

_log = getLogger(__name__)


class ModbusRWMixin:

    @staticmethod
    def read_modbus(obj: ModbusObj, device: ModbusDevice) -> Any:
        if not isinstance(device, ModbusDevice):
            raise HTTPBadGateway(reason="Isn't modbus device")
        try:
            registers = device.read(cmd_code=obj.properties.func_read,
                                    reg_address=obj.properties.address,
                                    quantity=obj.properties.quantity
                                    )
        except Exception as e:
            _log.error(f'Error: {e}',
                       exc_info=True
                       )
            return HTTPBadGateway(reason=str(e))

        if obj.properties.quantity == 1:
            return registers.pop()
        else:
            raise NotImplementedError

    @staticmethod
    def write_modbus(value, obj: ModbusObj, device: ModbusDevice) -> None:
        if not isinstance(device, ModbusDevice):
            raise HTTPBadGateway(reason="Isn't modbus device")

        try:
            device.write(cmd_code=obj.properties.func_write,
                         reg_address=obj.properties.address,
                         values=value
                         )
        except Exception as e:
            _log.error(f'Error: {e}',
                       exc_info=True
                       )
            raise HTTPBadGateway(reason=str(e))

from typing import Any

from aiohttp.web_exceptions import HTTPBadGateway

from gateway.api.handlers.base import BaseView
from gateway.connector.modbus import ModbusDevice
from gateway.models.modbus import ModbusObj
from logs import get_file_logger

_log = get_file_logger(logger_name=__name__)


class ModbusMixin(BaseView):
    @staticmethod
    def _modbus_read(obj: ModbusObj, device: ModbusDevice) -> Any:

        if not isinstance(device, ModbusDevice):
            raise HTTPBadGateway
        try:
            registers = device.read(cmd_code=obj.properties.func_read,
                                    reg_address=obj.properties.address,
                                    quantity=obj.properties.quantity
                                    )
        except Exception as e:
            _log.error(f'Error: {e}',
                       exc_info=True
                       )
            return HTTPBadGateway

        if obj.properties.quantity == 1:
            return registers.pop()
        else:
            raise NotImplementedError

    @staticmethod
    def _modbus_write(value, obj: ModbusObj, device: ModbusDevice) -> None:
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
                         values=value
                         )
        except Exception as e:
            _log.error(f'Error: {e}',
                       exc_info=True
                       )
            raise HTTPBadGateway

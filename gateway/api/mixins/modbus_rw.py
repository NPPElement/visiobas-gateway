from logging import getLogger
from typing import Any

from gateway.connectors import ModbusDevice
from gateway.models import ModbusObj

_log = getLogger(__name__)


class ModbusRWMixin:

    @staticmethod
    def read_modbus(obj: ModbusObj, device: ModbusDevice) -> Any:
        try:
            registers = device.read(obj=obj)

            if obj.properties.quantity == 1:
                return registers.pop()
            else:
                raise NotImplementedError

        except Exception as e:
            _log.error(f'Error: {e}',
                       exc_info=True
                       )

    @staticmethod
    def write_modbus(value, obj: ModbusObj, device: ModbusDevice) -> None:
        try:
            device.write(values=value,
                         obj=obj
                         )
        except Exception as e:
            _log.error(f'Error: {e}',
                       exc_info=True
                       )

    def write_with_check_modbus(self, value, obj: ModbusObj, device: ModbusDevice
                                ) -> bool:  # tuple[bool, tuple[Any, Any]]:
        """
        :return: tuple, where
                    [0]: the read value is equal to the written value
                    [1]: (value, rvalue)
        """
        self.write_modbus(value=value,
                          obj=obj,
                          device=device
                          )
        rvalue = self.read_modbus(obj=obj,
                                  device=device
                                  )
        return value == rvalue  # , (value, rvalue))

from logging import getLogger
from typing import Any

from ...connectors import ModbusDevice
from ...models import ModbusObj, ObjProperty

_log = getLogger(__name__)


class ModbusRWMixin:

    @staticmethod
    def read_modbus(obj: ModbusObj, device: ModbusDevice,
                    prop: ObjProperty = ObjProperty.presentValue) -> Any:
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
    def write_modbus(value, prop: ObjProperty, priority: int,
                     obj: ModbusObj, device: ModbusDevice) -> None:
        try:
            device.write(values=value,
                         obj=obj
                         )
        except Exception as e:
            _log.error(f'Error: {e}',
                       exc_info=True
                       )

    def write_with_check_modbus(self, value, prop: ObjProperty, priority: int
                                , obj: ModbusObj, device: ModbusDevice
                                ) -> bool:  # tuple[bool, tuple[Any, Any]]:
        """
        :return: the read value is equal to the written value
        """
        self.write_modbus(value=value,
                          obj=obj,
                          device=device
                          )
        rvalue = self.read_modbus(obj=obj,
                                  device=device
                                  )
        return value == rvalue  # , (value, rvalue))

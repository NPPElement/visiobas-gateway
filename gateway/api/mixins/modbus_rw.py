from typing import Optional, Union

from ...devices import AsyncModbusDevice  # todo use alias
from ...models import ObjProperty
from ...utils import get_file_logger

_LOG = get_file_logger(name=__name__)

# Aliases
AsyncModbusDeviceAlias = '...devices.AsyncModbusDevice'
ModbusObjAlias = '...models.ModbusObj'


class ModbusRWMixin:
    @staticmethod
    async def read_modbus(obj: ModbusObjAlias, device: AsyncModbusDevice,
                          prop: ObjProperty = ObjProperty.presentValue
                          ) -> Optional[Union[int, float]]:
        """
        Args:
            obj: Object instance.
            device: Device instance.

        Returns:
            Read value.
        """
        try:
            value = await device.read(obj=obj)  # FIXME async
            return value

        except Exception as e:
            _LOG.exception('Unhandled error',
                           extra={'device_id': device.id, 'object_id': obj.id, 'exc': e, })

    @staticmethod
    async def write_modbus(value: Union[int, float],
                           obj: ModbusObjAlias, device: AsyncModbusDevice,
                           prop: ObjProperty = ObjProperty.presentValue,
                           priority: int = 11, ) -> None:
        """
        Args:
            value: Value to write.
            obj: Object instance.
            device: Device instance.
            priority: Priority of value.
        """
        try:
            await device.write(value=value, obj=obj)  # FIXME async
        except Exception as e:
            _LOG.exception('Unhandled error',
                           extra={'device_id': device.id, 'object_id': obj.id, 'exc': e, })

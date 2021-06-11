from typing import Any

from ...models import BACnetObj, ObjProperty
from ...utils import get_file_logger

_LOG = get_file_logger(name=__name__)

# Aliases
BACnetDeviceAlias = Any  # '...devices.BACnetDevice'


class BACnetRWMixin:

    @staticmethod
    async def read_bacnet(prop: ObjProperty, obj: BACnetObj, device: BACnetDeviceAlias
                          ) -> Any:
        try:
            value = await device.async_read_property(obj=obj, prop=prop)
            return value
        except Exception as e:
            _LOG.exception('Unhandled error',
                           extra={'device_id': device.id, 'object_id': obj.id,
                                  'object_type': obj.type, 'exc': e, })

    @staticmethod
    async def write_bacnet(value, prop: ObjProperty, priority: int,
                           obj: BACnetObj, device: BACnetDeviceAlias) -> bool:
        """
        Args:
            value: Value to read.
            prop: Property for value.
            priority: Priority of value.
            obj: Object instance.
            device: Device instance.

        Returns:
            Is write successful.
        """
        try:
            return await device.async_write_property(value=value,
                                                     prop=prop,
                                                     priority=priority,
                                                     obj=obj
                                                     )
        except Exception as e:
            _LOG.exception('Unhandled error',
                           extra={'device_id': device.id, 'object_id': obj.id, 'exc': e, })

    # def write_with_check_bacnet(self, value, prop: ObjProperty, priority: int,
    #                             obj: BACnetObj, device: BACnetDeviceAlias) -> bool:
    #     """
    #     :return: the read value is equal to the written value
    #     """
    #     self.write_bacnet(value=value,
    #                       prop=prop,
    #                       priority=priority,
    #                       obj=obj,
    #                       device=device
    #                       )
    #     rvalue = self.read_bacnet(prop=prop,
    #                               obj=obj,
    #                               device=device
    #                               )
    #     return value == rvalue

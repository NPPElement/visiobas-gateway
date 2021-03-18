from logging import getLogger
from typing import Any

from ...connectors import BACnetDevice
from ...models import BACnetObj, ObjProperty

_log = getLogger(__name__)


class BACnetRWMixin:

    @staticmethod
    def read_bacnet(prop: ObjProperty, obj: BACnetObj, device: BACnetDevice) -> Any:
        try:
            value = device.read_property(obj=obj,
                                         prop=prop
                                         )
            return value
        except Exception as e:
            _log.warning(f'Error: {e}',
                         exc_info=True
                         )

    @staticmethod
    def write_bacnet(value, prop: ObjProperty, priority: int,
                     obj: BACnetObj, device: BACnetDevice) -> bool:
        """
        :return: is write successful
        """
        try:
            return device.write_property(value=value,
                                         prop=prop,
                                         priority=priority,
                                         obj=obj
                                         )
        except Exception as e:
            _log.warning(f'Error: {e}',
                         exc_info=True
                         )

    def write_with_check_bacnet(self, value, prop: ObjProperty, priority: int,
                                obj: BACnetObj, device: BACnetDevice) -> bool:
        """
        :return: the read value is equal to the written value
        """
        self.write_bacnet(value=value,
                          prop=prop,
                          priority=priority,
                          obj=obj,
                          device=device
                          )
        rvalue = self.read_bacnet(prop=prop,
                                  obj=obj,
                                  device=device
                                  )
        return value == rvalue

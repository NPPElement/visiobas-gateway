from logging import getLogger
from typing import Any

from gateway.connectors import BACnetDevice
from gateway.models import BACnetObj, ObjProperty

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

from functools import lru_cache
from typing import Optional, Any

from ...utils import get_file_logger

_LOG = get_file_logger(name=__name__)

# Aliases
VisioBASGatewayAlias = Any  # '...gateway_.VisioBASGateway'
DeviceAlias = Any  # Union['...devices.AsyncModbusDevice',]
ObjAlias = Any  # Union['...models.BACnetObj',]


class GetDevObjMixin:
    @staticmethod
    def get_device(dev_id: int, gtw: VisioBASGatewayAlias
                   ) -> Optional[DeviceAlias]:
        """Gets device instance from gateway instance.

        Args:
            dev_id: Device identifier.
            gtw: Gateway instance.

        Returns:
             Device instance.
        """
        return gtw.devices.get(dev_id)

    @staticmethod
    @lru_cache(maxsize=25)
    def get_obj(obj_id: int, obj_type_id: int, device: DeviceAlias
                ) -> Optional[ObjAlias]:
        """
        Args:
            obj_id: Object identifier.
            obj_type_id: Object type identifier.
            device: Device instance.

        Returns:
            Object instance.
        """
        try:
            for obj in device.objects:
                if obj.type.id == obj_type_id and obj.id == obj_id:
                    return obj
            # raise ValueError(
            #     f'Object type={obj_type_id} id={obj_id} not polling at {device}.')
        except AttributeError as e:
            _LOG.warning('Unhandled error',
                         extra={'device_id': device.id, 'object_id': obj_id,
                                'exc': e, })

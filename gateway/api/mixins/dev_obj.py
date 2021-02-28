from logging import getLogger

_log = getLogger(__name__)


class DevObjMixin:

    @staticmethod
    def get_device(dev_id: int, gateway):  # ->  Device(Thread)
        """Returns device's thread (for interactions with object)."""
        try:
            for con in gateway.connectors.values():
                if dev_id in con.polling_devices:
                    return con.polling_devices[dev_id]
            raise ValueError(f'Device[{dev_id}] not polling.')
        except AttributeError as e:
            _log.warning(f'Error: {e}',
                         exc_info=True
                         )

    @staticmethod
    def get_obj(device, obj_type: int, obj_id: int):  # -> ProtocolObj
        """Returns protocol's object."""
        try:
            for obj in device.objects:
                if obj.type.id == obj_type and obj.id == obj_id:
                    return obj
            raise ValueError(f'Object type={obj_type} id={obj_id} not polling at {device}.')
        except AttributeError as e:
            _log.warning(f'Error: {e}',
                         exc_info=True
                         )

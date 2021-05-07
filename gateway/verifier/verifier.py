from logging import getLogger
from typing import Collection

from ..models import StatusFlag, BACnetObjModel

_LOG = getLogger(__name__)


class BACnetVerifier:
    def __init__(self, config: dict):
        self._config = config

    @property
    def override_threshold(self) -> int:
        return self._config.get('override_threshold', 8)

    def __repr__(self) -> str:
        return self.__class__.__name__

    def verify_objects(self, objs: Collection[BACnetObjModel]):
        [self.verify(obj=obj) for obj in objs]

    def verify(self, obj: BACnetObjModel) -> None:
        self.verify_sf(obj=obj)
        self.verify_pv(obj=obj)

        if obj.pa is not None:
            self.verify_pa(obj=obj)

    @staticmethod
    def verify_sf(obj: BACnetObjModel) -> None:
        if isinstance(obj.sf, (list, tuple)) and len(obj.sf) == 4:
            obj.sf = int(''.join((str(flag)  # fixme use bit shifting?
                                  for flag in obj.sf)), base=2)
        elif not isinstance(obj.sf, int):
            _LOG.warning(f'Not supported sf: {obj.sf} {type(obj.sf)}')

    @staticmethod
    def verify_pv(obj: BACnetObjModel) -> None:
        if obj.pv == 'active':
            obj.pv = 1
        elif obj.pv == 'inactive':
            obj.pv = 0

        elif obj.pv is None:
            obj.pv = 'null'
            obj.sf = obj.sf | StatusFlag.FAULT.value
            # obj.reliability todo is reliability set?

        elif obj.pv == float('inf'):
            obj.pv = 'null'
            obj.sf = obj.sf | StatusFlag.FAULT.value
            obj.reliability = 2
        elif obj.pv == float('-inf'):
            obj.pv = 'null'
            obj.sf = obj.sf | StatusFlag.FAULT.value
            obj.reliability = 3

        elif isinstance(obj.pv, str) and not obj.pv.strip():
            obj.pv = 'null'
            obj.sf = obj.sf | StatusFlag.FAULT.value
            obj.reliability = 'empty'

    def verify_pa(self, obj: BACnetObjModel) -> None:
        """Sets OVERRIDE status flag if priority array contains override priority."""

        # todo: move priorities into Enum
        # MANUAL_LIFE_SAFETY = 9 - 1
        # AUTOMATIC_LIFE_SAFETY = 10 - 1
        # OVERRIDE_PRIORITIES = {MANUAL_LIFE_SAFETY,
        #                        AUTOMATIC_LIFE_SAFETY, }
        for i in range(len(obj.pa)):
            if obj.pa[i] is not None and i >= self.override_threshold:
                obj.sf |= StatusFlag.OVERRIDEN.value

    # def send_properties(self, device_id: int,
    #                     obj_name: str, properties: dict[ObjProperty, ...]) -> None:
    #     # TODO: add check out_of_service! (skip if enabled)
    #
    #     if properties[ObjProperty.statusFlags] == 0:
    #         self._send_via_mqtt(device_id=device_id,
    #                             obj_name=obj_name,
    #                             properties=properties
    #                             )
    #     else:
    #         self._collect_str_http(device_id=device_id, properties=properties)

    # def _collect_str_http(self, device_id: int,
    #                       properties: dict[ObjProperty, ...]) -> None:
    #     """Collect verified strings into storage.
    #     Sends collected strings from storage, when getting device_id from queue.
    #     """
    #     properties_str = self._to_str_http(properties=properties)
    #     try:
    #         self._http_storage[device_id].append(properties_str)
    #     except KeyError:
    #         self._http_storage[device_id] = [properties_str]

    def _send_via_http(self, device_id: int) -> None:
        """Send verified string from http_storage via HTTP."""
        try:
            device_str = ';'.join((*self._http_storage.pop(device_id), ''))
            self._http_queue.put((device_id, device_str))
        except KeyError:
            pass
        except Exception as e:
            _LOG.warning(f'HTTP Sending Error: {e}',
                         exc_info=True
                         )

from logging import getLogger

from ..models import ObjProperty, StatusFlag, BACnetObjModel

_LOG = getLogger(__name__)


class BACnetVerifier:
    def __repr__(self) -> str:
        return self.__class__.__name__

    def verify(self, obj: BACnetObjModel) -> BACnetObjModel:
        self.verify_sf(obj=obj)
        self.verify_pv(obj=obj)

        if obj.pa is not None:
            self.verify_pa(obj=obj)

        return obj

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

    @staticmethod
    def verify_pa(obj: BACnetObjModel) -> None:
        """Sets OVERRIDE status flag if priority array contains override priority."""

        # todo: move priorities into Enum
        MANUAL_LIFE_SAFETY = 9 - 1
        AUTOMATIC_LIFE_SAFETY = 10 - 1
        OVERRIDE_PRIORITIES = {MANUAL_LIFE_SAFETY,
                               AUTOMATIC_LIFE_SAFETY, }
        for i in range(len(obj.pa)):
            if obj.pa[i] is not None and i in OVERRIDE_PRIORITIES:
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

    def _send_via_mqtt(self, device_id: int, obj_name: str,
                       properties: dict[ObjProperty, ...]) -> None:
        """Send verified string via MQTT."""
        topic = obj_name.replace(':', '/').replace('.', '/')
        payload = self._to_str_mqtt(device_id=device_id,
                                    properties=properties
                                    )
        self._mqtt_queue.put((topic, payload))

    # @staticmethod
    # def _to_str_mqtt(device_id: int, properties: dict[ObjProperty, ...]) -> str:
    #     """Convert properties with statusFlags == 0 to str, for send via MQTT."""
    #     assert properties[ObjProperty.statusFlags] == 0
    #
    #     return '{0} {1} {2} {3} {4}'.format(device_id,
    #                                         properties[ObjProperty.objectIdentifier],
    #                                         properties[ObjProperty.objectType].id,
    #                                         properties[ObjProperty.presentValue],
    #                                         properties[ObjProperty.statusFlags]
    #                                         )

    # @staticmethod
    # def _to_str_http(properties: dict[ObjProperty, ...]) -> str:
    #     """Convert properties with statusFlags != 0 to str, for send via HTTP."""
    #     assert properties[ObjProperty.statusFlags] != 0
    #
    #     def convert_pa_to_str(pa: tuple) -> str:
    #         """Convert priority array tuple to str.
    #
    #         Result example: ,,,,,,,,40.5,,,,,,49.2,
    #         """
    #         return ','.join(
    #             ['' if priority is None else str(priority)
    #              for priority in pa]
    #         )
    #
    #     try:
    #         general_properties_str = '{0} {1} {2}'.format(
    #             properties[ObjProperty.objectIdentifier],
    #             properties[ObjProperty.objectType].id,
    #             properties[ObjProperty.presentValue]
    #         )
    #
    #         if ObjProperty.priorityArray in properties:
    #             pa_str = convert_pa_to_str(properties[ObjProperty.priorityArray])
    #             pa_sf_str = '{0} {1}'.format(pa_str, properties[ObjProperty.statusFlags])
    #
    #             general_properties_str += ' ' + pa_sf_str
    #             # return general_properties_str
    #         else:
    #             general_properties_str += ' {0}'.format(
    #                 properties[ObjProperty.statusFlags]
    #             )
    #
    #         if ObjProperty.reliability in properties:
    #             general_properties_str += ' {0}'.format(
    #                 properties[ObjProperty.reliability]
    #             )
    #
    #         # if ObjProperty.outOfService in verified_objects_properties:
    #         #     ...
    #         return general_properties_str
    #
    #     except KeyError:
    #         raise KeyError('Please provide all required properties. '
    #                        f'Properties received: {properties}')

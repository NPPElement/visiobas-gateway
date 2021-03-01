from logging import getLogger
from multiprocessing import Process, SimpleQueue

from ..models import ObjProperty, StatusFlag

_log = getLogger(__name__)


class BACnetVerifier(Process):
    def __init__(self, protocols_queue: SimpleQueue,
                 http_queue: SimpleQueue,
                 mqtt_queue: SimpleQueue,
                 config: dict):
        super().__init__(daemon=True)
        self._config = config
        # self._mqtt_enable = config.get('mqtt_enable', False)
        # self._http_enable = config.get('http_enable', True)

        self._protocols_queue = protocols_queue
        self._http_queue = http_queue
        self._mqtt_queue = mqtt_queue

        self._active = True

        # if self._http_enable:
        #     # Dict, where key - device_id,
        #     # value - list of collected verified strings
        self._http_storage: dict[int, list[str]] = {}
        #     self._http_queue = send_queue
        #
        # elif self._mqtt_enable:
        #     self._mqtt_queue = send_queue
        #
        # else:
        #     raise NotImplementedError('Select sending via HTTP ot MQTT')

    def __repr__(self) -> str:
        return self.__class__.__name__

    def run(self):
        _log.info(f'{self} Starting ...')
        while self._active:
            try:
                protocols_data = self._protocols_queue.get()

                if isinstance(protocols_data, int):
                    # These are not properties. This is a signal that
                    # the polling of the device is over.
                    # This means that the collected information on the device with
                    # that id must be sent to the http server.
                    device_id = protocols_data
                    _log.debug('Received signal to send collected data about '
                               f'Device[{device_id}] to HTTP server')
                    self._send_via_http(device_id=device_id)

                elif protocols_data and isinstance(protocols_data, dict):
                    # Received data about object from connectors
                    obj_properties = protocols_data

                    device_id = obj_properties.pop(ObjProperty.deviceId)
                    obj_name = obj_properties.pop(ObjProperty.objectName)

                    _log.debug(f'For Device [{device_id}] '
                               f'received properties: {obj_properties}')

                    # verifying all properties of the object
                    verified_obj_props = self.verify(obj_properties=obj_properties)
                    _log.debug(f'Verified properties: {verified_obj_props}')

                    # Sending verified object string into clients
                    self.send_properties(device_id=device_id,
                                         obj_name=obj_name,
                                         properties=verified_obj_props
                                         )
                    _log.debug('==================================================')
                else:
                    raise TypeError(f'Object of unexpected type provided: '
                                    f'{protocols_data} {type(protocols_data)}. '
                                    'Please provide device_id <int> '
                                    'to send data into HTTP server. '
                                    'Or provide <dict> with ObjProperties.'
                                    )

            except TypeError as e:
                _log.error(f'Verifying type error: {e}', exc_info=True)
            except KeyError as e:
                _log.error(f'Verifying key error: {e}', exc_info=True)
            except Exception as e:
                _log.error(f'Verifying error: {e}', exc_info=True)

        else:
            _log.info(f'{self} stopped.')

    # todo: make reliability Enum
    # todo: implement reliability concatenation

    def verify(self, obj_properties: dict[ObjProperty, ...]) -> dict[ObjProperty, ...]:

        verified_props = {
            ObjProperty.objectType: obj_properties[ObjProperty.objectType],
            ObjProperty.objectIdentifier: obj_properties[ObjProperty.objectIdentifier],
        }

        sf = obj_properties.get(ObjProperty.statusFlags, 0b0000)
        sf = self.verify_sf(sf=sf)
        verified_props[ObjProperty.statusFlags] = sf

        reliability = obj_properties.get(ObjProperty.reliability, 0)
        # self.verify_reliability()  implement if needs to verify reliability
        verified_props[ObjProperty.reliability] = reliability

        pv = obj_properties.get(ObjProperty.presentValue)
        verified_props = self.verify_pv(pv=pv, properties=verified_props)

        if obj_properties.get(ObjProperty.priorityArray) is not None:
            verified_props = self.verify_pa(pa=obj_properties[ObjProperty.priorityArray],
                                            properties=verified_props)

        return verified_props

    @staticmethod
    def verify_sf(sf: int or list) -> int:
        if isinstance(sf, int):
            return sf
        elif isinstance(sf, list) and len(sf) == 4:
            return int(''.join((str(flag) for flag in sf)), base=2)
        raise ValueError(f'Not supported sf: {sf} {type(sf)}')

    @staticmethod
    def verify_pv(pv, properties: dict[ObjProperty, ...]) -> dict[ObjProperty, ...]:

        verified_pv_props = properties.copy()

        if pv == 'active':
            verified_pv_props.update({ObjProperty.presentValue: 1})
        elif pv == 'inactive':
            verified_pv_props.update({ObjProperty.presentValue: 0})

        elif pv is None:
            sf = verified_pv_props.get(ObjProperty.statusFlags, 0b0000)
            sf = sf | StatusFlag.FAULT.value
            verified_pv_props.update({
                ObjProperty.presentValue: 'null',
                ObjProperty.statusFlags: sf,
                ObjProperty.reliability: verified_pv_props.get(ObjProperty.reliability, 7)
                # reliability sets as 65 earlier in BACnetObject if obj is unknown
            })
        elif pv == float('inf'):
            sf = verified_pv_props.get(ObjProperty.statusFlags, 0b0000)
            sf = sf | StatusFlag.FAULT.value
            verified_pv_props.update({ObjProperty.presentValue: 'null',
                                      ObjProperty.statusFlags: sf,
                                      ObjProperty.reliability: 2
                                      })
        elif pv == float('-inf'):
            sf = verified_pv_props.get(ObjProperty.statusFlags, 0b0000)
            sf = sf | StatusFlag.FAULT.value
            verified_pv_props.update({ObjProperty.presentValue: 'null',
                                      ObjProperty.statusFlags: sf,
                                      ObjProperty.reliability: 3
                                      })
        elif isinstance(pv, str) and not pv.strip():
            sf = verified_pv_props.get(ObjProperty.statusFlags, 0b0000)
            sf = sf | StatusFlag.FAULT.value
            verified_pv_props.update({
                ObjProperty.presentValue: 'null',
                ObjProperty.statusFlags: sf,
                ObjProperty.reliability: verified_pv_props.get(ObjProperty.reliability,
                                                               'empty')
                # reliability sets as 65 earlier in BACnetObject if obj is unknown
            })
        else:
            verified_pv_props.update({ObjProperty.presentValue: pv})
        return verified_pv_props

    @staticmethod
    def verify_pa(pa: tuple, properties: dict[ObjProperty, ...]
                  ) -> dict[ObjProperty, ...]:
        """Convert priorityArray to tuple."""
        verified_props = properties.copy()

        # todo: move priorities into Enum
        manual_life_safety = 9 - 1
        automatic_life_safety = 10 - 1
        override_priorities = {manual_life_safety,
                               automatic_life_safety
                               }
        for i in range(len(pa)):
            if pa[i] is not None and i in override_priorities:
                sf = verified_props.get(ObjProperty.statusFlags, 0b0000)
                sf = sf | StatusFlag.OVERRIDEN.value
                verified_props[ObjProperty.statusFlags] = sf

        verified_props[ObjProperty.priorityArray] = pa
        return verified_props

    def send_properties(self, device_id: int,
                        obj_name: str, properties: dict[ObjProperty, ...]) -> None:
        # TODO: add check out_of_service! (skip if enabled)

        if properties[ObjProperty.statusFlags] == 0:
            self._send_via_mqtt(device_id=device_id,
                                obj_name=obj_name,
                                properties=properties
                                )
        else:
            self._collect_str_http(device_id=device_id, properties=properties)

    def _collect_str_http(self, device_id: int,
                          properties: dict[ObjProperty, ...]) -> None:
        """Collect verified strings into storage.
        Sends collected strings from storage, when getting device_id from queue.
        """
        properties_str = self._to_str_http(properties=properties)
        try:
            self._http_storage[device_id].append(properties_str)
        except KeyError:
            self._http_storage[device_id] = [properties_str]

    def _send_via_http(self, device_id: int) -> None:
        """Send verified string from http_storage via HTTP."""
        try:
            device_str = ';'.join((*self._http_storage.pop(device_id), ''))
            self._http_queue.put((device_id, device_str))
        except Exception as e:
            _log.error(f'HTTP Sending Error: {e}',
                       # exc_info=True
                       )

    def _send_via_mqtt(self, device_id: int, obj_name: str,
                       properties: dict[ObjProperty, ...]) -> None:
        """Send verified string via MQTT."""
        topic = obj_name.replace(':', '/').replace('.', '/')
        payload = self._to_str_mqtt(device_id=device_id,
                                    properties=properties
                                    )
        self._mqtt_queue.put((topic, payload))

    @staticmethod
    def _to_str_mqtt(device_id: int, properties: dict[ObjProperty, ...]) -> str:
        """Convert properties with statusFlags == 0 to str, for send via MQTT."""
        assert properties[ObjProperty.statusFlags] == 0

        return '{0} {1} {2} {3} {4}'.format(device_id,
                                            properties[ObjProperty.objectIdentifier],
                                            properties[ObjProperty.objectType].id,
                                            properties[ObjProperty.presentValue],
                                            properties[ObjProperty.statusFlags]
                                            )

    @staticmethod
    def _to_str_http(properties: dict[ObjProperty, ...]) -> str:
        """Convert properties with statusFlags != 0 to str, for send via HTTP."""
        assert properties[ObjProperty.statusFlags] != 0

        def convert_pa_to_str(pa: tuple) -> str:
            """Convert priority array tuple to str.

            Result example: ,,,,,,,,40.5,,,,,,49.2,
            """
            return ','.join(
                ['' if priority is None else str(priority)
                 for priority in pa]
            )

        try:
            general_properties_str = '{0} {1} {2}'.format(
                properties[ObjProperty.objectIdentifier],
                properties[ObjProperty.objectType].id,
                properties[ObjProperty.presentValue]
            )

            if ObjProperty.priorityArray in properties:
                pa_str = convert_pa_to_str(properties[ObjProperty.priorityArray])
                pa_sf_str = '{0} {1}'.format(pa_str, properties[ObjProperty.statusFlags])

                general_properties_str += ' ' + pa_sf_str
                # return general_properties_str
            else:
                general_properties_str += ' {0}'.format(
                    properties[ObjProperty.statusFlags]
                )

            if ObjProperty.reliability in properties:
                general_properties_str += ' {0}'.format(
                    properties[ObjProperty.reliability]
                )

            # if ObjProperty.outOfService in verified_objects_properties:
            #     ...
            return general_properties_str

        except KeyError:
            raise KeyError('Please provide all required properties. '
                           f'Properties received: {properties}')

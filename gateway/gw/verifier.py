from multiprocessing import Process, SimpleQueue
from pathlib import Path

from bacpypes.basetypes import PriorityArray

from gateway.connectors.bacnet import ObjProperty, StatusFlags
from gateway.logs import get_file_logger

_base_path = Path(__file__).resolve().parent.parent
_log_file_path = _base_path / f'logs/{__name__}.log'

_log = get_file_logger(logger_name=__name__,
                       size_bytes=50_000_000,
                       file_path=_log_file_path)


class BACnetVerifier(Process):
    def __init__(self, protocols_queue: SimpleQueue,
                 http_queue: SimpleQueue,
                 config: dict):
        super().__init__(daemon=True)

        self.__config = config

        self.__protocols_queue = protocols_queue
        self.__http_queue = http_queue

        self.__active = True

        self.__mqtt_enable = config.get('mqtt_enable', False)
        self.__http_enable = config.get('http_enable', True)

        # Dict, where key - device_id, and value - list of collected verified strings
        if self.__http_enable:
            self.__http_storage: dict[int, list[str]] = {}

        # self.start()

    def __repr__(self):
        return 'BACnetVerifier'

    def run(self):
        _log.info(f'{self} Starting ...')
        while self.__active:
            try:
                protocols_data = self.__protocols_queue.get()

                if isinstance(protocols_data, int):
                    # These are not properties. This is a signal that
                    # the polling of the device is over.
                    # This means that the collected information on the device with
                    # that id must be sent to the http server.
                    device_id = protocols_data
                    _log.debug('Received signal to send collected data about '
                               f'Device[{device_id}] to HTTP server')
                    self.__http_send_to_server(device_id=device_id)

                elif protocols_data and isinstance(protocols_data, dict):
                    # Received data about object from the BACnet/Modbus-Connectors
                    obj_properties = protocols_data

                    device_id = obj_properties.pop(ObjProperty.deviceId)
                    obj_name = obj_properties.pop(ObjProperty.objectName)

                    _log.debug(f'For Device [{device_id}] '
                               f'received properties: {obj_properties}')

                    # verifying all properties of the object
                    verified_object_properties = self.verify(obj_properties=obj_properties)
                    _log.debug(f'Verified properties: {verified_object_properties}')

                    # representing all properties of the object as string
                    str_verified_obj_properties = self.convert_properties_to_str(
                        verified_object_properties)
                    _log.debug(f'Verified properties as str: {str_verified_obj_properties}')

                    # Sending verified object string into clients
                    self.send_verified_str(
                        device_id=device_id,
                        obj_name=obj_name,
                        verified_str=str_verified_obj_properties)
                    _log.debug('==================================================')
                else:
                    raise TypeError(f'Object of unexpected type provided: '
                                    f'{protocols_data} {type(protocols_data)}. '
                                    'Please provide device_id <int> '
                                    'to send data into HTTP server. '
                                    'Or provide <dict> with ObjProperties.')

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
        verified_properties = {
            ObjProperty.objectType: obj_properties[ObjProperty.objectType],
            ObjProperty.objectIdentifier: obj_properties[ObjProperty.objectIdentifier],
        }

        sf = StatusFlags(obj_properties.get(ObjProperty.statusFlags, [0, 0, 0, 0]))
        # self.verify_sf()  use if needs to verify statusFlags
        verified_properties[ObjProperty.statusFlags] = sf

        reliability = obj_properties.get(ObjProperty.reliability, 0)
        # self.verify_reliability()  use if needs to verify reliability
        verified_properties[ObjProperty.reliability] = reliability

        pv = obj_properties.get(ObjProperty.presentValue, 'null')
        self.verify_pv(pv=pv, properties=verified_properties)
        # Verified_properties updates in verify_pv()

        if ObjProperty.priorityArray in obj_properties:
            if not obj_properties[ObjProperty.priorityArray] is None:
                self.verify_pa(pa=obj_properties[ObjProperty.priorityArray],
                               properties=verified_properties)
            # Verified properties updates in verify_pa()
            # PriorityArray represent as tuple

        return verified_properties

    @staticmethod
    def verify_pv(pv, properties: dict[ObjProperty, ...]) -> None:
        # if (
        #         pv != 'null' and
        #         pv != float('inf') and
        #         pv != float('-inf') and
        #         not (isinstance(pv, str) and not pv.strip())
        # ):  # Extra check for better readability.

        if pv == 'null':
            sf = properties.get(ObjProperty.statusFlags, StatusFlags())
            sf.set(fault=True)
            properties.update({
                ObjProperty.presentValue: 'null',
                ObjProperty.statusFlags: sf,
                ObjProperty.reliability: properties.get(ObjProperty.reliability, 7)
                # reliability sets as 65 earlier in BACnetObject if obj is unknown
            })
        elif pv == float('inf'):
            sf = properties.get(ObjProperty.statusFlags, StatusFlags())
            sf.set(fault=True)
            properties.update({
                ObjProperty.presentValue: 'null',
                ObjProperty.statusFlags: sf,
                ObjProperty.reliability: 2
            })
        elif pv == float('-inf'):
            sf = properties.get(ObjProperty.statusFlags, StatusFlags())
            sf.set(fault=True)
            properties.update({
                ObjProperty.presentValue: 'null',
                ObjProperty.statusFlags: sf,
                ObjProperty.reliability: 3
            })
        elif isinstance(pv, str) and not pv.strip():
            sf = properties.get(ObjProperty.statusFlags, StatusFlags())
            sf.set(fault=True)
            properties.update({
                ObjProperty.presentValue: 'null',
                ObjProperty.statusFlags: sf,
                ObjProperty.reliability: properties.get(ObjProperty.reliability,
                                                        'empty')
                # reliability sets as 65 earlier in BACnetObject if obj is unknown
            })
        else:  # positive case
            if pv == 'active':
                pv = 1
            elif pv == 'inactive':
                pv = 0
            properties.update({
                ObjProperty.presentValue: pv
            })

    @staticmethod
    def verify_pa(pa: PriorityArray, properties: dict) -> None:
        """ Extract priorityArray into a tuple
        """
        pa_size = pa.value[0]
        priorities = []

        # todo: move priorities into Enum
        manual_life_safety = 9
        automatic_life_safety = 10
        override_priorities = {manual_life_safety,
                               automatic_life_safety
                               }

        for i in range(1, pa_size + 1):
            priority = pa.value[i]
            key, value = zip(*priority.dict_contents().items())
            if key[0] == 'null':
                priorities.append('')
            else:
                priorities.append(round(float(value[0])))
                if i in override_priorities:
                    sf = properties.get(ObjProperty.statusFlags, StatusFlags())
                    sf.set(overriden=True)
                    properties[ObjProperty.statusFlags] = sf

        properties[ObjProperty.priorityArray] = tuple(priorities)

    # @staticmethod
    def convert_properties_to_str(self, verified_objects_properties: dict) -> str:
        try:
            general_properties_str = ' '.join((
                str(verified_objects_properties[ObjProperty.objectIdentifier]),
                str(verified_objects_properties[ObjProperty.objectType].id),
                str(verified_objects_properties[ObjProperty.presentValue])
            ))

            if ObjProperty.priorityArray in verified_objects_properties:
                pa_str = self.convert_pa_to_str(
                    verified_objects_properties[ObjProperty.priorityArray])
                pa_sf_str = ' '.join((
                    pa_str,
                    str(verified_objects_properties[ObjProperty.statusFlags])
                ))
                general_properties_str = ' '.join((general_properties_str, pa_sf_str))
                return general_properties_str
            else:
                # statusFlags converts to binary value at __repr__ method
                sf_str = str(verified_objects_properties[ObjProperty.statusFlags])
                general_properties_str = ' '.join((general_properties_str, sf_str))

                if ObjProperty.reliability in verified_objects_properties:
                    reliability_str = str(
                        verified_objects_properties[ObjProperty.reliability])
                    general_properties_str = ' '.join((
                        general_properties_str,
                        reliability_str
                    ))

                # if ObjProperty.outOfService in verified_objects_properties:
                #     ...

                return general_properties_str

        except KeyError:
            raise KeyError('Please provide all required properties. '
                           f'Properties received: {verified_objects_properties}')

    @staticmethod
    def convert_pa_to_str(pa: tuple) -> str:
        """ Converts priority array tuple to str like ,,,,,,,,40.5,,,,,,49.2,
        """
        return ','.join([str(priority) for priority in pa])

    def send_verified_str(self, device_id: int,
                          obj_name: str, verified_str: str) -> None:
        """ If HTTP enable, collect data in http_storage
            If MQTT enable send data to broker
        """
        if self.__http_enable:
            _log.debug('Collecting verified str to http storage')
            self.__http_collect_str(device_id=device_id, verified_str=verified_str)
        if self.__mqtt_enable:
            self.__mqtt_send_to_broker(obj_name=obj_name, verified_str=verified_str)

    def __http_collect_str(self, device_id: int, verified_str: str) -> None:
        """ Collect verified strings into into storage.
            Sends collected strings from storage, when getting device_id from queue
        """
        try:
            self.__http_storage[device_id].append(verified_str)
        except KeyError:
            self.__http_storage[device_id] = [verified_str]

    def __http_send_to_server(self, device_id: int) -> None:
        """ Sends verified data from http_storage to HTTP server
        """
        try:
            device_str = ';'.join((*self.__http_storage.pop(device_id), ''))
            self.__http_queue.put((device_id, device_str))
        except Exception as e:
            _log.error(f'HTTP Sending Error: {e}', exc_info=True)

    def __mqtt_send_to_broker(self, obj_name: str, verified_str: str) -> None:
        """ Send verified strings to MQTT broker
        """
        topic = obj_name.replace(':', '/').replace('.', '/')
        # ...
        raise NotImplementedError

import logging
from logging.handlers import RotatingFileHandler
from multiprocessing import Process
from multiprocessing import SimpleQueue
from pathlib import Path

from bacpypes.basetypes import PriorityArray

from vb_gateway.connectors.bacnet.object_property import ObjProperty
from vb_gateway.connectors.bacnet.status_flags import StatusFlags


class BACnetVerifier(Process):
    def __init__(self, bacnet_queue: SimpleQueue, client_queue: SimpleQueue,
                 *,
                 http_enable: bool = False,
                 mqtt_enable: bool = False):
        super().__init__(daemon=True)

        self.__logger = logging.getLogger(f'{self}-Process')

        base_path = Path(__file__).resolve().parent.parent.parent
        log_path = base_path / f'logs/{__name__}.log'
        handler = RotatingFileHandler(filename=log_path,
                                      mode='a',
                                      maxBytes=50_000,
                                      encoding='utf-8')
        LOGGER_FORMAT = '%(levelname)-8s [%(asctime)s] [%(threadName)s] %(name)s - (%(filename)s).%(funcName)s(%(lineno)d): %(message)s'
        formatter = logging.Formatter(LOGGER_FORMAT)
        handler.setFormatter(formatter)
        self.__logger.addHandler(handler)

        self.__connector_queue = bacnet_queue
        self.__client_queue = client_queue

        self.__active = True

        self.__mqtt_enable = mqtt_enable
        self.__http_enable = http_enable

        # Dict, where key - device_id, and value - list of collected verified strings
        if http_enable:
            self.__http_storage = {}

        self.start()

    def __repr__(self):
        return 'BACnetVerifier'

    def run(self):
        self.__logger.info(f'{self} Starting ...')
        while self.__active:
            try:
                data = self.__connector_queue.get()

                if isinstance(data, int):
                    # These are not properties. This is a signal that
                    # the polling of the device is over.
                    # This means that the collected information on the device with
                    # that id can be sent to the http server.
                    device_id = data
                    self.__logger.debug('Received signal to send collected data about '
                                        f'Device[{device_id}] to HTTP server')
                    self.__http_send_to_server(device_id=device_id)

                elif data and isinstance(data, dict):
                    # Received data about object from the BACnetConnector
                    obj_properties = data
                    self.__logger.debug(f'Received properties: {obj_properties}')

                    device_id = obj_properties.pop(ObjProperty.deviceId)
                    obj_name = obj_properties.pop(ObjProperty.objectName)

                    # verifying all properties of the object
                    verified_object_properties = self.verify(obj_properties=obj_properties)
                    self.__logger.debug(
                        f'Verified properties: {verified_object_properties}')

                    # representing all properties of the object as string
                    str_verified_obj_properties = self.convert_properties_to_str(
                        verified_object_properties)
                    self.__logger.debug('Verified properties '
                                        f'as str: {str_verified_obj_properties}')

                    # Sending verified object string into clients
                    self.send_verified_str(
                        device_id=device_id,
                        obj_name=obj_name,
                        verified_str=str_verified_obj_properties)
                else:
                    raise TypeError(f'Object of unexpected type provided: '
                                    f'{data} {type(data)}. Please provide device_id <int> '
                                    'to send data into HTTP server. '
                                    'Or provide dict with ObjProperties.')

            except TypeError as e:
                self.__logger.error(f'Verifying type error: {e}', exc_info=True)
            except KeyError as e:
                self.__logger.error(f'Verifying key error: {e}', exc_info=True)
            except Exception as e:
                self.__logger.error(f'Verifying error: {e}', exc_info=True)

        else:
            self.__logger.info(f'{self} stopped.')

    # todo: make reliability Enum
    # todo: implement reliability concatenation

    def verify(self, obj_properties: dict) -> dict:
        verified_properties = {
            # ObjProperty.deviceId: obj_properties[ObjProperty.deviceId],
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
            self.verify_pa(pa=obj_properties[ObjProperty.priorityArray],
                           properties=verified_properties)
            # Verified properties updates in verify_pa()
            # PriorityArray represent as tuple

        return verified_properties

    @staticmethod
    def verify_pv(pv, properties: dict) -> None:
        if pv != 'null' and pv != float('inf') and pv != float('-inf'):
            if pv == 'active':
                pv = 1
            elif pv == 'inactive':
                pv = 0
            properties.update({
                ObjProperty.presentValue: pv
            })
            return None

        elif pv == 'null':
            sf = properties.get(ObjProperty.statusFlags, StatusFlags([0, 0, 0, 0]))
            sf.set(fault=True)
            properties.update({
                ObjProperty.presentValue: 'null',
                ObjProperty.statusFlags: sf,
                ObjProperty.reliability: properties.get(ObjProperty.reliability, 7)
                # reliability sets as 65 earlier in BACnetObject if obj is unknown
            })
            return None

        elif pv == float('inf'):
            sf = properties.get(ObjProperty.statusFlags, StatusFlags([0, 0, 0, 0]))
            sf.set(fault=True)
            properties.update({
                ObjProperty.presentValue: 'null',
                ObjProperty.statusFlags: sf,
                ObjProperty.reliability: 2
            })
            return None

        elif pv == float('-inf'):
            sf = properties.get(ObjProperty.statusFlags, StatusFlags([0, 0, 0, 0]))
            sf.set(fault=True)
            properties.update({
                ObjProperty.presentValue: 'null',
                ObjProperty.statusFlags: sf,
                ObjProperty.reliability: 3
            })
            return None

    @staticmethod
    def verify_pa(pa: PriorityArray, properties: dict) -> None:
        """ Extract priorityArray into a tuple
        """
        pa_size = pa.value[0]
        priorities = []

        # todo: move priorities into Enum
        manual_life_safety = 9

        for i in range(1, pa_size + 1):
            priority = pa.value[i]
            key, value = zip(*priority.dict_contents().items())
            if key[0] == 'null':
                priorities.append('')
            else:
                priorities.append(value[0])
                if i == manual_life_safety:
                    sf = properties.get(ObjProperty.statusFlags, StatusFlags([0, 0, 0, 0]))
                    sf.set(overriden=True)
                    properties[ObjProperty.statusFlags] = sf
        properties[ObjProperty.priorityArray] = tuple(priorities)

    # @staticmethod
    def convert_properties_to_str(self, verified_objects_properties: dict) -> str:
        try:
            general_properties_str = ' '.join((
                str(verified_objects_properties[ObjProperty.objectIdentifier]),
                verified_objects_properties[ObjProperty.objectType.name],
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
                          obj_name: str,
                          verified_str: str) -> None:
        """ If HTTP enable, collect data in http_storage
            If MQTT enable send data to broker
        """
        if self.__http_enable:
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
            self.__client_queue.put((device_id, device_str))
        except Exception as e:
            self.__logger.error(f'HTTP Sending Error: {e}')

    def __mqtt_send_to_broker(self, obj_name: str, verified_str: str) -> None:
        """ Send verified strings to MQTT broker
        """
        topic = obj_name.replace(':', '/').replace('.', '/')
        # ...
        raise NotImplementedError

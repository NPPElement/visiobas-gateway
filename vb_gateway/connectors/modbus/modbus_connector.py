import asyncio
from multiprocessing import SimpleQueue
from pathlib import Path
from threading import Thread
from time import sleep
from typing import Dict, Set, List

from aiohttp.web_exceptions import HTTPServerError, HTTPClientError

from vb_gateway.connectors.bacnet.obj_property import ObjProperty
from vb_gateway.connectors.bacnet.obj_type import ObjType
from vb_gateway.connectors.base_connector import Connector
from vb_gateway.connectors.modbus.device import ModbusDevice
from vb_gateway.connectors.modbus.object import ModbusObject
from vb_gateway.connectors.utils import read_address_cache, parse_modbus_properties
from vb_gateway.utility.utility import get_file_logger


class ModbusConnector(Thread, Connector):
    def __init__(self, gateway,
                 verifier_queue: SimpleQueue,
                 config: dict):
        super().__init__()

        base_path = Path(__file__).resolve().parent.parent.parent
        log_file_path = base_path / f'logs/{__name__}.log'

        self.__logger = get_file_logger(logger_name=f'{self}',
                                        file_size_bytes=50_000_000,
                                        file_path=log_file_path)

        self.__config = config
        self.setName(name=f'{self}-Thread')
        self.setDaemon(True)

        self.__gateway = gateway
        self.__verifier_queue = verifier_queue

        self.__connected = False
        self.__stopped = False

        self.__object_types_to_request = (
            ObjType.ANALOG_INPUT,
            ObjType.ANALOG_OUTPUT,
            ObjType.ANALOG_VALUE,

            ObjType.BINARY_INPUT,
            ObjType.BINARY_OUTPUT,
            ObjType.BINARY_VALUE,

            ObjType.MULTI_STATE_INPUT,
            ObjType.MULTI_STATE_OUTPUT,
            ObjType.MULTI_STATE_VALUE,
        )

        # Match device_id with device_address. Example: {200: '10.21.80.12'}
        self.__address_cache = {}
        self.__polling_devices = {}

    def __repr__(self):
        return 'ModbusConnector'

    def run(self):
        self.__logger.info(f'{self} starting ...')
        while not self.__stopped:

            base_dir = Path(__file__).resolve().parent.parent.parent
            address_cache_path = base_dir / 'connectors/modbus/address_cache'
            self.__address_cache = read_address_cache(address_cache_path=address_cache_path)

            # stop irrelevant devices
            irrelevant_devices_id = tuple(set(self.__polling_devices.keys()) - set(
                self.__address_cache.keys()))
            if irrelevant_devices_id:
                self.__stop_devices(devices_id=irrelevant_devices_id)

            try:  # Requesting objects and their types from the server
                # FIXME: move to client?
                devices_objects = self.get_devices_objects(
                    devices_id=tuple(self.__address_cache.keys()),
                    obj_types=self.__object_types_to_request)

                if devices_objects:  # If received devices with objects from the server
                    self.__logger.info('Received devices with '
                                       f'objects: {[*devices_objects.keys()]} '
                                       'Starting them ...')

                    # unpack json from server to BACnetObjects class
                    devices_objects = self.unpack_objects(objects=devices_objects)
                    self.update_devices(devices=devices_objects)
                    del devices_objects

                else:
                    self.__logger.error('No objects from server')
                    del devices_objects
                    continue

            except (HTTPServerError, HTTPClientError) as e:
                self.__logger.error('Error retrieving information about '
                                    f'devices objects from the server: {e}')
            except Exception as e:
                self.__logger.error(f'Device update error: {e}', exc_info=True)

            self.__logger.debug('Sleeping 1h ...')
            sleep(60 * 60)
            # FIXME REPLACE TO threading.Timer? in ThreadPoolExecutor?

        else:
            self.__logger.info(f'{self} stopped.')

    def open(self) -> None:
        self.__connected = True
        self.__stopped = False
        self.start()

    def close(self) -> None:
        self.__stopped = True
        self.__connected = False

        self.__stop_devices(devices_id=tuple(self.__polling_devices.keys()))

    def update_devices(self, devices: Dict[int, Set[ModbusObject]]) -> None:
        """ Starts Modbus devices threads
        """
        for dev_id, objs in devices.items():
            if dev_id in self.__polling_devices:
                self.__stop_device(device_id=dev_id)
            self.__start_device(device_id=dev_id, objects=objs)

        self.__logger.info('Devices updated')

    def __start_device(self, device_id, objects: Set[ModbusObject]) -> None:
        """ Start Modbus devise thread
        """
        self.__logger.debug(f'Starting Device [{device_id}] ...')
        try:
            self.__polling_devices[device_id] = ModbusDevice(
                verifier_queue=self.__verifier_queue,
                connector=self,
                address=self.__address_cache[device_id],
                device_id=device_id,
                objects=objects
            )

        except ConnectionError as e:
            self.__logger.error(f'Device [{device_id}] connection error: {e}')
        except Exception as e:
            self.__logger.error(f'Device [{device_id}] '
                                f'starting error: {e}', exc_info=True)

        else:
            self.__logger.info(f'Device [{device_id}] started')

    def __stop_device(self, device_id: int) -> None:
        """ Stop Modbus device thread
        """
        try:
            self.__logger.debug(f'Device [{device_id}] stopping polling ...')
            self.__polling_devices[device_id].stop_polling()
            self.__logger.debug(f'Device [{device_id}] stopped polling')
            self.__polling_devices[device_id].join()
            self.__logger.debug(f'Device [{device_id}]-Thread stopped')

        except KeyError as e:
            self.__logger.error(f'The device with id {device_id} is not running. '
                                f'Please provide the id of the polling device: {e}')
        except Exception as e:
            self.__logger.error(f'Device stopping error: {e}')

    def __stop_devices(self, devices_id: tuple) -> None:
        """ Stop Modbus devices threads
        """
        try:
            [self.__stop_device(device_id=device_id) for device_id in devices_id]
            for dev_id in devices_id:
                del self.__polling_devices[dev_id]
        except Exception as e:
            self.__logger.error(f'Stopping devices error: {e}', exc_info=True)
        else:
            self.__logger.info(f'Modbus devices [{devices_id}] were stopping')

    def get_devices_objects(self,
                            devices_id: tuple,
                            obj_types: tuple) -> Dict[int, Dict[ObjType, List[dict]]]:

        devices_objs = asyncio.run(
            self.__gateway.http_client.rq_devices_objects(devices_id=devices_id,
                                                          obj_types=obj_types))
        return devices_objs

    def unpack_objects(self,
                       objects: Dict[int, Dict[ObjType, List[dict]]]) -> Dict[
        int, Set[ModbusObject]]:
        """ Makes BACnetObjects from device structure, received from the server
        """
        devices_objects = {dev_id: set() for dev_id in objects.keys()}

        for dev_id, objs_by_types in objects.items():
            for obj_type, objects in objs_by_types.items():
                for obj in objects:
                    obj_type = obj_type
                    obj_id = obj[str(ObjProperty.objectIdentifier.id)]
                    obj_name = obj[str(ObjProperty.objectName.id)]

                    property_list = obj[str(ObjProperty.propertyList.id)]
                    if property_list is not None:
                        address, quantity, func_read = parse_modbus_properties(
                            property_list=property_list)

                        modbus_obj = ModbusObject(type=obj_type, id=obj_id, name=obj_name,
                                                  address=address, quantity=quantity,
                                                  func_read=func_read)
                        devices_objects[dev_id].add(modbus_obj)
                    else:
                        self.__logger.warning(f'{ObjProperty.propertyList} is: '
                                              f'{property_list} for Modbus object: '
                                              f'Device [{dev_id}] ({obj_type}, {obj_id})')

        return devices_objects

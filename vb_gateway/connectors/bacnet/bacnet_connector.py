import asyncio
from json import loads
from multiprocessing import SimpleQueue
from pathlib import Path
from threading import Thread
from time import sleep
from typing import Dict, Set, List, Tuple

import BAC0
from BAC0.core.io.IOExceptions import InitializationError, NetworkInterfaceException
from aiohttp.web_exceptions import HTTPClientError, HTTPServerError

from vb_gateway.connectors.bacnet.device import BACnetDevice
from vb_gateway.connectors.bacnet.obj_property import ObjProperty
from vb_gateway.connectors.bacnet.obj_type import ObjType
from vb_gateway.connectors.bacnet.object import BACnetObject
from vb_gateway.connectors.base_connector import Connector
from vb_gateway.connectors.utils import read_address_cache
from vb_gateway.utility.utility import get_file_logger


class BACnetConnector(Thread, Connector):
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
        self.default_update_period = config.get('default_update_period', 10)

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

        self.__network = None

    def __repr__(self):
        return 'BACnetConnector'

    def run(self):
        self.__logger.info(f'{self} starting ...')
        while not self.__stopped:

            base_dir = Path(__file__).resolve().parent.parent.parent
            address_cache_path = base_dir / 'connectors/bacnet/address_cache'
            self.__address_cache = read_address_cache(address_cache_path=address_cache_path)

            # stop irrelevant devices
            irrelevant_devices_id = tuple(set(self.__polling_devices.keys()) - set(
                self.__address_cache.keys()))
            if irrelevant_devices_id:
                self.__stop_devices(devices_id=irrelevant_devices_id)

            if self.__network:  # IF HAVING INITIALIZED NETWORK
                try:  # Requesting objects and their types from the server
                    # FIXME: move to client?
                    devices_objects = self.get_devices_objects(
                        devices_id=tuple(self.__address_cache.keys()),
                        obj_types=self.__object_types_to_request)

                    if devices_objects:  # If received devices with objects from the server
                        self.__logger.info('Received devices with '
                                           f'objects: {[*devices_objects.keys()]} '
                                           'Requesting update intervals for them ...')

                        self.__update_itervals = self.get_devices_update_interval(
                            devices_id=tuple(self.__address_cache.keys()),
                            default_update_interval=self.default_update_period
                        )
                        self.__logger.info('Received update intervals for devices.'
                                           'Starting them ...')

                        # Unpack json from server to BACnetObjects class
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
                # except OSError as e:
                #     self.__logger.error(f'Please, check login: {e}')
                except Exception as e:
                    self.__logger.error(f'Device update error: {e}', exc_info=True)

                self.__logger.debug('Sleeping 1h ..')
                sleep(60 * 60)
                # FIXME REPLACE TO threading.Timer? in ThreadPoolExecutor?

            else:  # IF NOT HAVE INITIALIZED BAC0 NETWORK
                self.__logger.info('Initializing BAC0 network ...')
                try:
                    self.__network = BAC0.lite()
                    BAC0.log_level('silence')  # fixme: no reaction - still having debug

                except (InitializationError,
                        NetworkInterfaceException) as e:
                    self.__logger.error(f'Network initialization error: {e}', exc_info=True)
                else:
                    self.__logger.info('Network initialized.')
        else:
            self.__network.disconnect()
            self.__logger.info('BAC0 Network disconnected.')
            self.__logger.info(f'{self} stopped.')

    def open(self) -> None:
        self.__connected = True
        self.__stopped = False
        self.start()

    def close(self) -> None:
        self.__stopped = True
        self.__connected = False

        self.__stop_devices(devices_id=tuple(self.__polling_devices.keys()))

    def update_devices(self, devices: Dict[int, Set[BACnetObject]],
                       update_intervals: Dict[int, int]) -> None:
        """ Starts BACnet devices threads
        """
        for device_id, objects in devices.items():
            if device_id not in self.__polling_devices:
                self.__stop_device(device_id=device_id)
            self.__start_device(device_id=device_id, objects=objects,
                                update_interval=update_intervals[device_id])

        self.__logger.info('Devices updated')

    def __start_device(self, device_id: int, objects: Set[BACnetObject],
                       update_interval: int) -> None:
        """ Start BACnet device thread
        """
        self.__logger.debug(f'Starting Device [{device_id}] ...')
        try:
            self.__polling_devices[device_id] = BACnetDevice(
                verifier_queue=self.__verifier_queue,
                connector=self,
                address=self.__address_cache[device_id],
                device_id=device_id,
                network=self.__network,
                objects=objects,
                update_period=update_interval
            )
        except Exception as e:
            self.__logger.error(f'Device [{device_id}] '
                                f'starting error: {e}', exc_info=True)
        else:
            self.__logger.info(f'Device [{device_id}] started')

    def __stop_devices(self, devices_id: tuple) -> None:
        """ Stops BACnet Devices threads
        """
        try:
            [self.__stop_device(device_id=device_id) for device_id in devices_id]
            for dev_id in devices_id:
                del self.__polling_devices[dev_id]

        except Exception as e:
            self.__logger.error(f'Stopping devices error: {e}', exc_info=True)
        else:
            self.__logger.info(f'BACnet devices [{devices_id}] were stopping')

    def __stop_device(self, device_id: int) -> None:
        """ Stop device by device_id
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

    def get_devices_objects(self, devices_id: tuple,
                            obj_types: tuple) -> Dict[int, Dict[ObjType, List[dict]]]:
        """ Requests objects for modbus connector from server via http client
        """
        devices_objs = asyncio.run(
            self.__gateway.http_client.rq_devices_objects(devices_id=devices_id,
                                                          obj_types=obj_types))
        return devices_objs

    def get_devices_update_interval(self, devices_id: Tuple[int],
                                    default_update_interval: int = 10) -> Dict[int, int]:

        device_objs = asyncio.run(self.__gateway.http_client.rq_devices_objects(
            devices_id=devices_id,
            obj_types=(ObjType.DEVICE,)
        ))

        devices_intervals = {}

        # Extract update_interval from server's response
        for dev_id, obj_types in device_objs.items():
            try:
                prop_371 = obj_types[ObjType.DEVICE][0][str(ObjProperty.propertyList.id)]
                upd_interval = loads(prop_371)['update_interval']
                devices_intervals[dev_id] = upd_interval
            except LookupError as e:
                self.__logger.error(
                    f'Update interval for Device [{dev_id}] cannot be extracted: {e}')
                devices_intervals[dev_id] = default_update_interval

        # devices_intervals = {
        #     dev_id: loads(obj_types[ObjType.DEVICE][0][str(ObjProperty.propertyList.id)])[
        #         'update_interval'] for dev_id, obj_types in device_objs.items()
        # }

        return devices_intervals

    @staticmethod
    def unpack_objects(
            objects: Dict[int, Dict[ObjType, List[dict]]]) -> Dict[int, Set[BACnetObject]]:
        """ Makes BACnetObjects from device structure, received from the server
        """
        devices_objects = {dev_id: set() for dev_id in objects.keys()}

        for dev_id, objs_by_types in objects.items():
            for obj_type, objects in objs_by_types.items():
                for obj in objects:
                    obj_type = obj_type
                    obj_id = obj[str(ObjProperty.objectIdentifier.id)]
                    obj_name = obj[str(ObjProperty.objectName.id)]

                    bacnet_obj = BACnetObject(type=obj_type, id=obj_id, name=obj_name)
                    devices_objects[dev_id].add(bacnet_obj)

        return devices_objects

import asyncio
from json import loads
from multiprocessing import SimpleQueue
from pathlib import Path
from threading import Thread
from time import sleep

from aiohttp.web_exceptions import HTTPServerError, HTTPClientError

from vb_gateway.connectors import Connector
from vb_gateway.connectors.bacnet import ObjProperty, ObjType
from vb_gateway.connectors.modbus import ModbusObject, VisioModbusProperties
from vb_gateway.connectors.modbus.device import ModbusDevice
from vb_gateway.logs import get_file_logger

_base_path = Path(__file__).resolve().parent.parent.parent
_log_file_path = _base_path / f'logs/{__name__}.log'

_log = get_file_logger(logger_name=__name__,
                       size_bytes=50_000_000,
                       file_path=_log_file_path)


class ModbusConnector(Thread, Connector):
    def __init__(self, gateway,
                 verifier_queue: SimpleQueue,
                 config: dict):
        super().__init__()

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
        # self.__not_connect_devices: set[int, ...] = set()

        self.__update_intervals = {}

    def __repr__(self):
        return 'ModbusConnector'

    def run(self):
        _log.info(f'{self} starting ...')
        while not self.__stopped:

            # base_dir = Path(__file__).resolve().parent.parent.parent
            address_cache_path = _base_path / 'connectors/modbus/address_cache'
            self.__address_cache = self.read_address_cache(
                address_cache_path=address_cache_path)

            # stop irrelevant devices
            irrelevant_devices_id = tuple(set(self.__polling_devices.keys()) - set(
                self.__address_cache.keys()))
            if irrelevant_devices_id:
                self.__stop_devices(devices_id=irrelevant_devices_id)

            try:  # Requesting objects and their types from the server
                # FIXME: move to client
                devices_objects = self.get_devices_objects(
                    devices_id=tuple(self.__address_cache.keys()),
                    obj_types=self.__object_types_to_request)

                if devices_objects:  # If received devices with objects from the server
                    _log.info('Received devices with '
                              f'objects: {[*devices_objects.keys()]} '
                              'Requesting update intervals for them ...')

                    self.__update_intervals = self.get_devices_update_interval(
                        devices_id=tuple(self.__address_cache.keys()),
                        default_update_interval=self.default_update_period
                    )
                    _log.info('Received update intervals for devices.'
                              'Starting them ...')

                    # Unpack json from server to BACnetObjects class
                    devices_objects = self.unpack_objects(objects=devices_objects)
                    self.update_devices(devices=devices_objects,
                                        update_intervals=self.__update_intervals)
                    del devices_objects

                else:
                    _log.error('No objects from server')
                    del devices_objects
                    continue

            except (HTTPServerError, HTTPClientError, OSError) as e:
                _log.error('Error retrieving information about '
                           f'devices objects from the server: {e}')
            except Exception as e:
                _log.error(f'Device update error: {e}', exc_info=True)

            _log.debug('Sleeping 1h ...')
            sleep(60 * 60)
            # FIXME REPLACE TO threading.Timer? in ThreadPoolExecutor?

        else:
            _log.info(f'{self} stopped.')

    def open(self) -> None:
        self.__connected = True
        self.__stopped = False
        self.start()

    def close(self) -> None:
        self.__stopped = True
        self.__connected = False

        self.__stop_devices(devices_id=tuple(self.__polling_devices.keys()))

    def update_devices(self, devices: dict[int, set[ModbusObject]],
                       update_intervals: dict[int, int]) -> None:
        """ Starts Modbus devices threads
        """
        for dev_id, objs in devices.items():
            if dev_id in self.__polling_devices.keys():
                self.__stop_device(device_id=dev_id)
            self.__start_device(device_id=dev_id, objects=objs,
                                update_interval=update_intervals[dev_id])

        _log.info('Devices updated')

    def __start_device(self, device_id: int, objects: set[ModbusObject],
                       update_interval: int) -> None:
        """ Start Modbus devise thread
        """
        _log.debug(f'Starting Device [{device_id}] ...')
        try:
            self.__polling_devices[device_id] = ModbusDevice(
                verifier_queue=self.__verifier_queue,
                connector=self,
                address=self.__address_cache[device_id],
                device_id=device_id,
                objects=objects,
                update_period=update_interval
            )
        # except ConnectionError as e:
        #     _log.error(f'Device [{device_id}] connection error: {e}')
        #     self.__not_connect_devices.add(device_id)
        except Exception as e:
            _log.error(f'Device [{device_id}] '
                       f'starting error: {e}', exc_info=True)

        else:
            _log.info(f'Device [{device_id}] started')

    def __stop_device(self, device_id: int) -> None:
        """ Stop Modbus device thread
        """
        try:
            _log.debug(f'Device [{device_id}] stopping polling ...')
            self.__polling_devices[device_id].stop_polling()
            _log.debug(f'Device [{device_id}] stopped polling')
            self.__polling_devices[device_id].join()
            _log.debug(f'Device [{device_id}]-Thread stopped')

        except KeyError as e:
            _log.error(f'The device with id {device_id} is not running. '
                       f'Please provide the id of the polling device: {e}')
        except Exception as e:
            _log.error(f'Device stopping error: {e}')

    def __stop_devices(self, devices_id: tuple) -> None:
        """ Stop Modbus devices threads
        """
        try:
            [self.__stop_device(device_id=device_id) for device_id in devices_id]
            for dev_id in devices_id:
                del self.__polling_devices[dev_id]
        except Exception as e:
            _log.error(f'Stopping devices error: {e}', exc_info=True)
        else:
            _log.info(f'Modbus devices [{devices_id}] were stopping')

    def get_devices_objects(self, devices_id: tuple[int],
                            obj_types: tuple[ObjType, ...]
                            ) -> dict[int, dict[ObjType, list[dict]]]:

        devices_objs = asyncio.run(
            self.__gateway.http_client.rq_devices_objects(devices_id=devices_id,
                                                          obj_types=obj_types))
        return devices_objs

    def get_devices_update_interval(self, devices_id: tuple[int],
                                    default_update_interval: int = 10) -> dict[int, int]:
        """ Receive update intervals for devices via http client
        """

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
                _log.error(
                    f'Update interval for Device [{dev_id}] cannot be extracted: {e}')
                devices_intervals[dev_id] = default_update_interval

        # devices_intervals = {
        #     dev_id: loads(obj_types[ObjType.DEVICE][0][str(ObjProperty.propertyList.id)])[
        #         'update_interval'] for dev_id, obj_types in device_objs.items()
        # }

        return devices_intervals

    def unpack_objects(self, objects: dict[int, dict[ObjType, list[dict]]]) -> \
            dict[int, set[ModbusObject]]:
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
                        address, quantity, func_read, props = self.extract_properties(
                            property_list=property_list)

                        modbus_obj = ModbusObject(type=obj_type,
                                                  id=obj_id,
                                                  name=obj_name,

                                                  address=address,
                                                  quantity=quantity,
                                                  func_read=func_read,

                                                  properties=props
                                                  )
                        devices_objects[dev_id].add(modbus_obj)
                    else:
                        _log.warning(f'{ObjProperty.propertyList} is: '
                                     f'{property_list} for Modbus object: '
                                     f'Device [{dev_id}] ({obj_type}, {obj_id})')

        return devices_objects

    @staticmethod
    def extract_properties(property_list: str
                           ) -> tuple[int, int, int, VisioModbusProperties]:
        try:
            modbus_properties = loads(property_list)['modbus']

            address = int(modbus_properties['address'])
            quantity = int(modbus_properties['quantity'])
            func_read = int(modbus_properties['functionRead'][-2:])

            scale = int(modbus_properties.get('scale', 1))
            data_type = modbus_properties['dataType']
            data_length = int(modbus_properties['dataLength'])
            byte_order = '<' if quantity == 1 else '>'

            bit = int(modbus_properties['bit']) if data_type == 'BOOL' else None,

            properties = VisioModbusProperties(scale=scale,
                                               data_type=data_type,
                                               data_length=data_length,
                                               byte_order=byte_order,
                                               bit=bit
                                               )
        except KeyError as e:
            raise e
        else:
            return address, quantity, func_read, properties

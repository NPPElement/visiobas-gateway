import asyncio
from json import loads
from multiprocessing import SimpleQueue
from pathlib import Path
from time import sleep

from aiohttp.web_exceptions import HTTPServerError, HTTPClientError

from gateway.connectors import Connector
from gateway.connectors.bacnet import ObjProperty, ObjType
from gateway.connectors.modbus import ModbusObj, VisioModbusProperties
from gateway.connectors.modbus.device import ModbusDevice
from gateway.logs import get_file_logger

_base_path = Path(__file__).resolve().parent.parent.parent

_log = get_file_logger(logger_name=__name__,
                       size_bytes=50_000_000
                       )


class ModbusConnector(Connector):
    __slots__ = ('_config', 'default_update_period', '_gateway', '_verifier_queue',
                 '_connected', '_stopped', 'obj_types_to_request',
                 'address_cache', 'polling_devices', '_update_intervals'
                 )

    def __init__(self, gateway, verifier_queue: SimpleQueue, config: dict):

        super().__init__(gateway=gateway,
                         verifier_queue=verifier_queue,
                         config=config
                         )

        # todo move to http client
        self.obj_types_to_request = (
            ObjType.ANALOG_INPUT, ObjType.ANALOG_OUTPUT, ObjType.ANALOG_VALUE,
            ObjType.BINARY_INPUT, ObjType.BINARY_OUTPUT, ObjType.BINARY_VALUE,
            ObjType.MULTI_STATE_INPUT, ObjType.MULTI_STATE_OUTPUT,
            ObjType.MULTI_STATE_VALUE,
        )

    def __repr__(self):
        return 'ModbusConnector'

    def run(self):
        _log.info(f'{self} starting ...')
        while not self._stopped:

            # base_dir = Path(__file__).resolve().parent.parent.parent
            address_cache_path = _base_path / 'connectors/modbus/address_cache'
            self._address_cache = self.read_address_cache(
                address_cache_path=address_cache_path)

            # stop irrelevant devices
            irrelevant_devices_id = tuple(set(self.polling_devices.keys()) - set(
                self._address_cache.keys()))
            if irrelevant_devices_id:
                self.stop_devices(devices_id=irrelevant_devices_id)

            try:  # Requesting objects and their types from the server
                # FIXME: move to client
                devices_objects = self.get_devices_objects(
                    devices_id=tuple(self._address_cache.keys()),
                    obj_types=self.obj_types_to_request)

                if devices_objects:  # If received devices with objects from the server
                    _log.info('Received devices with '
                              f'objects: {[*devices_objects.keys()]} '
                              'Requesting update intervals for them ...'
                              )

                    self._update_intervals = self.get_devices_update_interval(
                        devices_id=tuple(self._address_cache.keys()),
                        default_update_interval=self.default_update_period
                    )
                    _log.info('Received update intervals for devices. '
                              'Starting them ...')

                    # Unpack json from server to BACnetObjects class
                    devices_objects = self.unpack_objects(objects=devices_objects)
                    self.update_devices(devices=devices_objects,
                                        update_intervals=self._update_intervals)
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

    def start_device(self, device_id: int, objs: set[ModbusObj],
                     upd_interval: int) -> None:
        """Start Modbus device thread."""
        _log.debug(f'Starting Device [{device_id}] ...')
        try:
            self.polling_devices[device_id] = ModbusDevice(
                verifier_queue=self._verifier_queue,
                connector=self,
                address=self._address_cache[device_id],
                device_id=device_id,
                objects=objs,
                update_period=upd_interval
            )
            _log.info(f'Device [{device_id}] started')
        # except ConnectionError as e:
        #     _log.error(f'Device [{device_id}] connection error: {e}')
        #     self.__not_connect_devices.add(device_id)
        except Exception as e:
            _log.error(f'Device [{device_id}] starting error: {e}',
                       exc_info=True
                       )

    def get_devices_objects(self, devices_id: tuple[int],
                            obj_types: tuple[ObjType, ...]
                            ) -> dict[int, dict[ObjType, list[dict]]]:

        devices_objs = asyncio.run(
            self._gateway.http_client.upd_device(
                node=self._gateway.http_client.get_node,
                devices_id=devices_id,
                obj_types=obj_types
            ))
        return devices_objs

    def get_devices_update_interval(self, devices_id: tuple[int],
                                    default_update_interval: int = 10) -> dict[int, int]:
        """ Receive update intervals for devices via http client
        """
        device_objs = asyncio.run(
            self._gateway.http_client.upd_device(
                node=self._gateway.http_client.get_node,
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
            dict[int, set[ModbusObj]]:
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

                        # todo: is typename correct?
                        modbus_obj = ModbusObj(typename='ModbusObject',
                                               type=obj_type,
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
            data_length = modbus_properties.get('dataLength', None)
            bit = modbus_properties.get('bit', None)

            # byte_order = '<' if quantity == 1 else '>'
            # byte_order = None  # don't use now # todo

            # trying to fill the data if it is not enough
            if data_type == 'BOOL' and bit is None and data_length is None:
                data_length = 16
            elif data_type == 'BOOL' and isinstance(bit, int) and data_length is None:
                data_length = 1
            elif data_type != 'BOOL' and data_length is None and isinstance(quantity, int):
                data_length = quantity * 16

            properties = VisioModbusProperties(scale=scale,
                                               data_type=data_type,
                                               data_length=data_length,
                                               # byte_order=byte_order,
                                               bit=bit
                                               )
            _log.debug(f'Received: {modbus_properties}\n'
                       f'Extracted properties: {properties}')
        except KeyError as e:
            raise e
        else:
            return address, quantity, func_read, properties

import asyncio
from json import loads
from multiprocessing import SimpleQueue
from pathlib import Path
from time import sleep

from BAC0 import lite
from BAC0.core.io.IOExceptions import InitializationError, NetworkInterfaceException
from aiohttp.web_exceptions import HTTPClientError, HTTPServerError

from gateway.connectors import Connector
from gateway.connectors.bacnet import ObjProperty, ObjType, BACnetObj
from gateway.connectors.bacnet.device import BACnetDevice
from gateway.logs import get_file_logger

_base_path = Path(__file__).resolve().parent.parent.parent

_log = get_file_logger(logger_name=__name__,
                       size_bytes=50_000_000
                       )


class BACnetConnector(Connector):
    __slots__ = ('_config', '__interfaces', '_network',
                 'default_update_period', '_gateway', '_verifier_queue',
                 '_connected', '_stopped',
                 'obj_types_to_request', 'address_cache',
                 'polling_devices', '_update_intervals'
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
        return 'BACnetConnector'

    def run(self):
        _log.info(f'{self} starting ...')
        while not self._stopped:

            # base_dir = Path(__file__).resolve().parent.parent.parent
            address_cache_path = _base_path / 'connectors/bacnet/address_cache'
            self._address_cache = self.read_address_cache(
                address_cache_path=address_cache_path)

            if len(self.polling_devices) > 0:
                # Check irrelevant devices. Stop them, if found
                irrelevant_devices_id = tuple(set(self.polling_devices.keys()) - set(
                    self._address_cache.keys()))
                if irrelevant_devices_id:
                    self.__stop_devices(devices_id=irrelevant_devices_id)

            if self._network:  # IF HAVING INITIALIZED NETWORKS
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
                                  'Starting them ...'
                                  )

                        # Unpack json from server to BACnetObjects class
                        devices_objects = self.unpack_objects(objects=devices_objects)

                        self.update_devices(devices=devices_objects,
                                            update_intervals=self._update_intervals)
                    else:
                        _log.warning('No objects from server')
                        sleep(60)  # fixme
                        continue

                except (HTTPServerError, HTTPClientError, OSError) as e:
                    _log.error('Error retrieving information about '
                               f'devices objects from the server: {e}')
                except Exception as e:
                    _log.error(f'Device update error: {e}', exc_info=True)
                finally:
                    del devices_objects

                _log.info('Sleeping 1h ..')
                sleep(60 * 60)
                # FIXME REPLACE TO threading.Timer? in ThreadPoolExecutor?

            else:  # IF NOT HAVE INITIALIZED BAC0 NETWORK
                _log.info('Initializing BAC0 network ...')
                try:
                    self._network = lite()
                except (InitializationError, NetworkInterfaceException) as e:
                    _log.error(f'Network initialization error: {e}', exc_info=True)
                    sleep(10)  # delay before next try
                else:
                    _log.debug('BAC0 network initialized.')
        else:
            self._network.disconnect()
            _log.info(f'{self} stopped.')

    def start_device(self, device_id: int, objs: set[BACnetObj],
                     upd_interval: int) -> None:
        """Start BACnet device thread."""
        _log.debug(f'Starting Device [{device_id}] ...')
        try:
            self.polling_devices[device_id] = BACnetDevice(
                verifier_queue=self._verifier_queue,
                connector=self,
                address=self._address_cache[device_id],
                device_id=device_id,
                network=self._network,
                objects=objs,
                update_period=upd_interval
            )
            _log.info(f'Device [{device_id}] started')
        except Exception as e:
            _log.error(f'Device [{device_id}] starting error: {e}',
                       exc_info=True
                       )

    def get_devices_objects(self, devices_id: tuple[int],
                            obj_types: tuple) -> dict[int, dict[ObjType, list[dict]]]:
        """ Requests objects for modbus connector from server via http client """
        devices_objs = asyncio.run(
            self._gateway.http_client.upd_device(
                node=self._gateway.http_client.get_node,
                devices_id=devices_id,
                obj_types=obj_types
            ))
        return devices_objs

    def get_devices_update_interval(self, devices_id: tuple[int],
                                    default_update_interval: int) -> dict[int, int]:
        """ Receive update intervals for devices via http client """
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
                _log.warning(
                    f'Update interval for Device [{dev_id}] cannot be extracted: {e}')
                devices_intervals[dev_id] = default_update_interval

        # devices_intervals = {
        #     dev_id: loads(obj_types[ObjType.DEVICE][0][str(ObjProperty.propertyList.id)])[
        #         'update_interval'] for dev_id, obj_types in device_objs.items()
        # }

        return devices_intervals

    @staticmethod
    def unpack_objects(
            objects: dict[int, dict[ObjType, list[dict]]]) -> dict[int, set[BACnetObj]]:
        """ Makes BACnetObjects from device structure, received from the server
        """
        devices_objects = {dev_id: set() for dev_id in objects.keys()}

        for dev_id, objs_by_types in objects.items():
            for obj_type, objects in objs_by_types.items():
                for obj in objects:
                    obj_type = obj_type
                    obj_id = obj[str(ObjProperty.objectIdentifier.id)]
                    obj_name = obj[str(ObjProperty.objectName.id)]

                    bacnet_obj = BACnetObj(type=obj_type, id=obj_id, name=obj_name)
                    devices_objects[dev_id].add(bacnet_obj)

        return devices_objects

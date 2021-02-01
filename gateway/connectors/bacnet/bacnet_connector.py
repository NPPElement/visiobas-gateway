from json import loads
from multiprocessing import SimpleQueue
from pathlib import Path
from time import sleep

from BAC0 import lite
from BAC0.core.io.IOExceptions import InitializationError, NetworkInterfaceException

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

    def __init__(self, gateway, http_queue: SimpleQueue,
                 verifier_queue: SimpleQueue, config: dict):

        super().__init__(gateway=gateway,
                         http_queue=http_queue,
                         verifier_queue=verifier_queue,
                         config=config
                         )
        self._network = None

        self.address_cache_path = _base_path / 'connectors/bacnet/address_cache'

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

            # # base_dir = Path(__file__).resolve().parent.parent.parent
            # address_cache_path = _base_path / 'connectors/bacnet/address_cache'
            # self._address_cache = self.read_address_cache(
            #     address_cache_path=address_cache_path)
            #
            # if len(self.polling_devices) > 0:
            #     # Check irrelevant devices. Stop them, if found
            #     irrelevant_devices_id = tuple(set(self.polling_devices.keys()) - set(
            #         self._address_cache.keys()))
            #     if irrelevant_devices_id:
            #         self.__stop_devices(devices_id=irrelevant_devices_id)

            if self._network:  # IF HAVING INITIALIZED NETWORKS
                try:
                    # Requesting objects and their types from the server.
                    # Then stop received device (if need) and start updated.
                    self.run_update_devices_loop()

                except Exception as e:
                    _log.error(f'Device update error: {e}',
                               exc_info=True
                               )

            else:  # IF NOT HAVE INITIALIZED BAC0 NETWORK
                _log.info('Initializing BAC0 network ...')
                try:
                    self._network = lite()
                    _log.info('BAC0 network initialized.')

                except (InitializationError, NetworkInterfaceException) as e:
                    _log.error(f'Network initialization error: {e}',
                               exc_info=True
                               )
                    sleep(10)  # delay before next try

        else:
            self._network.disconnect()
            _log.info(f'{self} stopped.')

    def parse_objs_data(self, objs_data: dict[ObjType, list[dict]]
                        ) -> tuple[int, set[BACnetObj]]:
        """"""
        # TODO IMPLEMENT

    def start_device(self, device_id: int, objs: set[BACnetObj],
                     upd_interval: int) -> None:
        """Start BACnet device thread."""
        _log.debug(f'Starting Device [{device_id}] ...')
        try:
            self.polling_devices[device_id] = BACnetDevice(
                verifier_queue=self._verifier_queue,
                connector=self,
                address=self.address_cache[device_id],
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

    # TODO use in parse
    # def get_devices_update_interval(self, devices_id: tuple[int],
    #                                 default_update_interval: int) -> dict[int, int]:
    #     """ Receive update intervals for devices via http client """
    #     device_objs = asyncio.run(
    #         self._gateway.http_client.push_upd_device(
    #             node=self._gateway.http_client.get_node,
    #             devices_id=devices_id,
    #             obj_types=(ObjType.DEVICE,)
    #         ))
    #     devices_intervals = {}
    #
    #     # Extract update_interval from server's response
    #     for dev_id, obj_types in device_objs.items():
    #         try:
    #             prop_371 = obj_types[ObjType.DEVICE][0][str(ObjProperty.propertyList.id)]
    #             upd_interval = loads(prop_371)['update_interval']
    #             devices_intervals[dev_id] = upd_interval
    #         except LookupError as e:
    #             _log.warning(
    #                 f'Update interval for Device [{dev_id}] cannot be extracted: {e}')
    #             devices_intervals[dev_id] = default_update_interval
    #
    #     # devices_intervals = {
    #     #     dev_id: loads(obj_types[ObjType.DEVICE][0][str(ObjProperty.propertyList.id)])[
    #     #         'update_interval'] for dev_id, obj_types in device_objs.items()
    #     # }
    #
    #     return devices_intervals

    pass

    # TODO use in parse
    # @staticmethod
    # def unpack_objects(
    #         objects: dict[int, dict[ObjType, list[dict]]]) -> dict[int, set[BACnetObj]]:
    #     """ Makes BACnetObjects from device structure, received from the server
    #     """
    #     devices_objects = {dev_id: set() for dev_id in objects.keys()}
    #
    #     for dev_id, objs_by_types in objects.items():
    #         for obj_type, objects in objs_by_types.items():
    #             for obj in objects:
    #                 obj_type = obj_type
    #                 obj_id = obj[str(ObjProperty.objectIdentifier.id)]
    #                 obj_name = obj[str(ObjProperty.objectName.id)]
    #
    #                 bacnet_obj = BACnetObj(type=obj_type, id=obj_id, name=obj_name)
    #                 devices_objects[dev_id].add(bacnet_obj)
    #
    #     return devices_objects

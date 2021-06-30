# from logging import getLogger
# from multiprocessing import SimpleQueue
# from pathlib import Path
# from time import sleep
# from typing import Sequence
#
# from BAC0 import lite
# from BAC0.core.io.IOExceptions import InitializationError, NetworkInterfaceException
#
# from .device import BACnetDevice
# from ..base_connector import BaseConnector
# from ...models import ObjType, BACnetObjModel
#
# _base_path = Path(__file__).resolve().parent.parent.parent
# _log = getLogger(__name__)
#
#
# class BACnetConnector(BaseConnector):
#     # __slots__ = ('_config', '__interfaces', '_network',
#     #              'default_update_period', '_gateway', '_verifier_queue',
#     #              '_connected', '_stopped',
#     #              'obj_types_to_request', 'address_cache',
#     #              'polling_devices', '_update_intervals'
#     #              )
#
#     def __init__(self, gateway, getting_queue: SimpleQueue,
#                  verifier_queue: SimpleQueue, config: dict):
#
#         super().__init__(gateway=gateway,
#                          getting_queue=getting_queue,
#                          verifier_queue=verifier_queue,
#                          config=config
#                          )
#         self._network = None
#
#         self.address_cache_path = _base_path / 'connectors/bacnet/address_cache'
#
#         self.obj_types_to_request = (ObjType.ANALOG_INPUT, ObjType.ANALOG_OUTPUT,
#                                      ObjType.ANALOG_VALUE,
#                                      ObjType.BINARY_INPUT, ObjType.BINARY_OUTPUT,
#                                      ObjType.BINARY_VALUE,
#                                      ObjType.MULTI_STATE_INPUT, ObjType.MULTI_STATE_OUTPUT,
#                                      ObjType.MULTI_STATE_VALUE,
#                                      )
#
#     def run(self):
#         _log.info(f'{self} starting ...')
#         while not self._stopped:
#             if self._network:  # IF HAVING INITIALIZED NETWORKS
#                 try:
#                     # Requesting objects and their types from the server.
#                     # Then stop received device (if need) and start updated.
#                     self.run_getting_devices_loop()
#
#                 except Exception as e:
#                     _log.error(f'Device update error: {e}',
#                                exc_info=True
#                                )
#
#             else:  # IF NOT HAVE INITIALIZED BAC0 NETWORK
#                 _log.info('Initializing BAC0 network ...')
#                 try:
#                     self._network = lite()
#                     _log.info('BAC0 network initialized.')
#
#                 except (InitializationError, NetworkInterfaceException, Exception) as e:
#                     _log.error(f'Network initialization error: {e}',
#                                exc_info=True
#                                )
#                     # delay before next try
#                     sleep(self._config.get('delay_bac0_attempt', 30))
#
#         else:
#             self._network.disconnect()
#             _log.info(f'{self} stopped.')
#
#     def parse_objs_data(self,
#                         objs_data: list[dict]
#                         # objs_data: dict[ObjType, list[dict]]
#                         ) -> tuple[int, set[BACnetObjModel]]:
#         # Extract update period
#         # upd_period = self.parse_upd_period(device_obj_data=objs_data.pop(ObjType.DEVICE))
#         upd_period = 60  # FIXME
#         bacnet_objs = set()
#         # Create protocol objects from objs_data
#         for obj_data in objs_data:
#             try:
#                 bacnet_obj = BACnetObjModel(**obj_data)
#                 bacnet_objs.add(bacnet_obj)
#
#             except LookupError:
#                 _log.warning('Extract object error.')
#         return upd_period, bacnet_objs
#
#     def start_device(self, device_id: int, objs: set[BACnetObjModel],
#                      upd_interval: int) -> None:
#         """Start BACnet device thread."""
#         _log.debug(f'Starting Device [{device_id}] ...')
#         try:
#             self.polling_devices[device_id] = BACnetDevice(
#                 verifier_queue=self._verifier_queue,
#                 connector=self,
#                 address=self.address_cache[device_id],
#                 device_id=device_id,
#                 network=self._network,
#                 objects=objs,
#                 update_period=upd_interval
#             )
#             self.polling_devices[device_id].start()
#             _log.info(f'Device [{device_id}] started')
#         except Exception as e:
#             _log.error(f'Device [{device_id}] starting error: {e}',
#                        exc_info=True
#                        )

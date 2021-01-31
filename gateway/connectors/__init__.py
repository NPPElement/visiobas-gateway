from abc import ABC, abstractmethod
from ipaddress import IPv4Address
from multiprocessing import SimpleQueue
from pathlib import Path
from threading import Thread
from typing import Iterable

from gateway import get_file_logger
from gateway.connectors.bacnet import ObjProperty, ObjType, BACnetObj

_log = get_file_logger(logger_name=__name__,
                       size_bytes=50_000_000
                       )


class Connector(Thread, ABC):

    def __init__(self, gateway, verifier_queue: SimpleQueue, config: dict):
        super().__init__()
        self._config = config
        self._gateway = gateway
        self._verifier_queue = verifier_queue

        self.default_update_period = config.get('default_update_period', 10)

        self.setName(name=f'{self}-Thread')
        self.setDaemon(True)

        self._connected = False
        self._stopped = False

        # Match device_id with device_address. Example: {200: '10.21.80.12'}
        self.address_cache = {}
        self.polling_devices = {}
        self._update_intervals = {}

        self.obj_types_to_request: Iterable[ObjType] = ()

    @property
    def address_cache_ids(self) -> Iterable:
        return self.address_cache.keys()

    @abstractmethod
    def run(self):
        pass

    def open(self) -> None:
        self._connected = True
        self._stopped = False
        self.start()

    def close(self) -> None:
        self._stopped = True
        self._connected = False

        self.stop_devices(devices_id=tuple(self.polling_devices.keys()))

    @abstractmethod
    def update_devices(self, devices: dict[int, set],
                       update_intervals: dict[int, int]) -> None:
        """Start device thread.
        :param devices: dict - device_id: set of protocol objects
        :param update_intervals: dict - device_id: upd_period
        """

        for device_id, objects in devices.items():
            if device_id in self.polling_devices:
                self.stop_device(device_id=device_id)
            self.start_device(device_id=device_id,
                              objs=objects,
                              upd_interval=update_intervals[device_id]
                              )
        _log.info(f'Devices {[*devices.keys()]} updated')

    @abstractmethod
    def upd_device(self, device_id: int,
                   objs: dict[ObjType, list[dict]]) -> bool:
        """Receive data about device form HTTP client.
        Then parse it. After that start device thread.
        """
        # todo parse data
        upd_interval, objs = self.parse_objs_data()

        self.start_device(device_id=device_id,
                          objs=objs,
                          upd_interval=upd_interval
                          )

    @abstractmethod
    def parse_objs_data(self, objs: dict[ObjType, list[dict]]
                        ) -> tuple[int, set[BACnetObj]]:
        """Extract objects data from response."""
        pass

    @abstractmethod
    def start_device(self, device_id: int, objs: set[BACnetObj], upd_interval: int) -> None:
        pass
        # todo device - use factory
        #  use *args

    @abstractmethod
    def stop_device(self, device_id: int) -> None:
        """Stop device by id."""
        try:
            _log.debug(f'Device [{device_id}] stopping polling ...')
            self.polling_devices[device_id].stop_polling()
            _log.debug(f'Device [{device_id}] stopped polling')
            self.polling_devices[device_id].join()
            _log.debug(f'Device [{device_id}]-Thread stopped')

        except KeyError as e:
            _log.error(f'The device with id {device_id} is not running. '
                       f'Please provide the id of the polling device: {e}'
                       )
        except Exception as e:
            _log.error(f'Device stopping error: {e}',
                       exc_info=True
                       )

    def stop_devices(self, devices_id: Iterable) -> None:
        """Stop devices by id."""
        for dev_id in devices_id:
            try:
                self.stop_device(device_id=dev_id)
                del self.polling_devices[dev_id]
                # [self.stop_device(device_id=device_id) for device_id in devices_id]
                # self.polling_devices = {}  # fixme incorrect!
                _log.info(f'Device [{dev_id}] was stopped')

            except Exception as e:
                _log.error(f'Stopping device error: {e}',
                           exc_info=True
                           )

    @abstractmethod
    def __repr__(self):
        pass

    @abstractmethod
    def get_devices_objects(self, devices_id: list, obj_types: list):
        pass

    @staticmethod
    def read_address_cache(address_cache_path: Path) -> dict[int, str]:
        """ Updates address_cache file

            Parse text file format of address_cache.
            Add information about devices

            Example of address_cache format:

            ;Device   MAC (hex)            SNET  SADR (hex)           APDU
            ;-------- -------------------- ----- -------------------- ----
              200     0A:15:50:0C:BA:C0    0     00                   480
              300     0A:15:50:0D:BA:C0    0     00                   480
              400     0A:15:50:0E:BA:C0    0     00                   480
              500     0A:15:50:0F:BA:C0    0     00                   480
              600     0A:15:50:10:BA:C0    0     00                   480
            ;
            ; Total Devices: 5
        """
        try:
            text = address_cache_path.read_text(encoding='utf-8')
        except FileNotFoundError as e:
            raise e

        address_cache = {}

        for line in text.split('\n'):
            trimmed = line.strip()
            if not trimmed.startswith(';') and trimmed:
                try:
                    device_id, mac, _, _, apdu = trimmed.split(maxsplit=4)
                    # In mac we have ip-address host:port in hex
                    device_id = int(device_id)
                    addr1, addr2, addr3, addr4, port1, port2 = mac.rsplit(':', maxsplit=5)
                    addr = IPv4Address('.'.join((
                        str(int(addr1, base=16)),
                        str(int(addr2, base=16)),
                        str(int(addr3, base=16)),
                        str(int(addr4, base=16)))))
                    port = int(port1 + port2, base=16)
                    address_cache[device_id] = ':'.join((str(addr), str(port)))
                except ValueError:
                    continue
        return address_cache


def get_fault_obj_properties(reliability: int or str,
                             pv='null',
                             sf: list = None) -> dict:
    """ Returns properties for unknown objects
    """
    if sf is None:
        sf = [0, 1, 0, 0]
    return {
        ObjProperty.presentValue: pv,
        ObjProperty.statusFlags: sf,
        ObjProperty.reliability: reliability
        #  todo: make reliability class as Enum
    }

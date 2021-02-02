from abc import ABC, abstractmethod
from functools import lru_cache
from ipaddress import IPv4Address
from json import loads
from multiprocessing import SimpleQueue
from pathlib import Path
from threading import Thread
from typing import Iterable

from gateway.logs import get_file_logger
from gateway.models.bacnet import ObjType, BACnetObj, ObjProperty

_log = get_file_logger(logger_name=__name__,
                       size_bytes=50_000_000
                       )


class Connector(Thread, ABC):
    """Base class for all connectors."""

    def __init__(self, gateway, http_queue: SimpleQueue,
                 verifier_queue: SimpleQueue, config: dict):
        super().__init__()
        self._config = config
        self._gateway = gateway

        self.http_queue = http_queue
        self._verifier_queue = verifier_queue

        self.setName(name=f'{self}-Thread')
        self.setDaemon(True)

        self._connected = False
        self._stopped = False

        self.address_cache_path = None
        self.polling_devices = {}

        self.default_upd_period = config.get('default_upd_period', 10)

        self.obj_types_to_request: Iterable[ObjType] = ()

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

        # Close all running devices
        self.stop_devices(devices_id=self.polling_devices.keys())

        # Clear the read_address_cache cache to read the updated `address_cache` file.
        self.read_address_cache.clear_cache()

    def run_update_devices_loop(self) -> None:
        """Receive data about device form HTTP client.
        Then parse it. After that start device thread.
        """
        while not self._stopped:
            try:
                dev_id, objs_data = self.http_queue.get()

                if objs_data:

                    upd_interval, objs = self.parse_objs_data(objs_data=objs_data)

                    is_stopped = self.stop_device(device_id=dev_id)
                    if is_stopped:
                        self.start_device(device_id=dev_id,
                                          objs=objs,
                                          upd_interval=upd_interval
                                          )
                else:
                    _log.warning('No objects from HTTP.')
                    # todo: request obj faster?
            except Exception as e:
                _log.error(f'Update device error: {e}',
                           exc_info=True
                           )

    @abstractmethod
    def parse_objs_data(self, objs_data: dict[ObjType, list[dict]]
                        ) -> tuple[int, set[BACnetObj]]:
        """Extract objects data from response."""
        pass

    # @abstractmethod
    def parse_upd_period(self, device_obj_data: list[dict]) -> int:
        """Extract device update period from device object."""
        try:
            prop_list = device_obj_data[0][str(ObjProperty.propertyList.id)]
            upd_period = loads(prop_list)['update_interval']
        except LookupError as e:
            _log.warning(f'Update interval cannot be extracted: {e}')
            upd_period = self.default_upd_period
        return upd_period

    @abstractmethod
    def start_device(self, device_id: int, objs: set[BACnetObj], upd_interval: int) -> None:
        pass

    def stop_device(self, device_id: int) -> bool:
        """Stop device by id.

        todo: devices must be a threads and implement stop_polling() method

        :param device_id:
        :return: is device closed
        """
        try:
            _log.debug(f'Device [{device_id}] stopping polling ...')
            self.polling_devices[device_id].stop_polling()
            _log.debug(f'Device [{device_id}] stopped polling')
            self.polling_devices[device_id].join()
            _log.debug(f'Device [{device_id}]-Thread stopped')
            return True

        except KeyError as e:
            _log.error(f'The device with id {device_id} is not running. '
                       f'Please provide the id of the polling device: {e}'
                       )
            return True
        except Exception as e:
            _log.error(f'Device stopping error: {e}',
                       exc_info=True
                       )
            return False

    def stop_devices(self, devices_id: Iterable[int]) -> None:
        """Stop devices by id."""
        for dev_id in devices_id:
            try:
                self.stop_device(device_id=dev_id)
                del self.polling_devices[dev_id]
                _log.info(f'Device [{dev_id}] was stopped')

            except Exception as e:
                _log.error(f'Stopping device error: {e}',
                           exc_info=True
                           )

    def __repr__(self) -> str:
        return self.__class__.__name__

    @property
    def address_cache_ids(self) -> Iterable[int]:
        return list(self.address_cache.keys())

    @property
    def address_cache(self) -> dict[int, str]:
        """Match device_id with device_address.

        :return: Example: {200: '10.21.80.12:47808'}
        """
        return self.read_address_cache(address_cache_path=self.address_cache_path
                                       )

    @lru_cache(maxsize=1)
    def read_address_cache(self, address_cache_path: Path) -> dict[int, str]:
        """Updates address_cache file.
        Caches the read result. Therefore, the cache must be cleared on update.

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

        :return: Example:
            200: '10.21.80.200:47808'
        """
        try:
            address_cache = {}

            text = address_cache_path.read_text(encoding='utf-8')
            for line in text.split('\n'):
                trimmed = line.strip()
                if not trimmed.startswith(';') and trimmed:
                    try:
                        device_id, mac, _, _, apdu = trimmed.split(maxsplit=4)
                        # In mac we have ip-address host:port in hex
                        device_id = int(device_id)
                        addr1, addr2, addr3, addr4, port1, port2 = mac.rsplit(':',
                                                                              maxsplit=5)
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

        except Exception as e:
            _log.critical(f'Read address_cache error: {e} '
                          # f'Closing {self}'
                          )
            # self.close()  # fixme?
            # raise e

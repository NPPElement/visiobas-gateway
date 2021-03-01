# import atexit
from abc import ABC, abstractmethod
from json import loads
from logging import getLogger
from multiprocessing import SimpleQueue
from threading import Thread
from typing import Iterable

from ..models import ObjType, BACnetObj, ObjProperty
from ..utils import read_address_cache

_log = getLogger(__name__)


class BaseConnector(Thread, ABC):
    """Base class for all connectors."""

    def __init__(self, gateway, getting_queue: SimpleQueue,
                 verifier_queue: SimpleQueue, config: dict):
        super().__init__()
        self.setName(name=f'{self}-Thread')
        self.setDaemon(True)

        self._config = config
        self._gateway = gateway

        self.getting_queue = getting_queue
        self._verifier_queue = verifier_queue

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

    # @atexit.register
    def close(self) -> None:
        self._stopped = True
        self._connected = False

        # Close all running devices
        self.stop_devices(devices_id=self.polling_devices.keys())

        # Clear the read_address_cache cache to read the updated `address_cache` file.
        self.read_address_cache.clear_cache()

    def run_getting_devices_loop(self) -> None:
        """Receive data about device form HTTP client.
        Then parse it. After that start device thread.
        """
        while not self._stopped:
            try:
                dev_id, objs_data = self.getting_queue.get()

                if objs_data:

                    upd_interval, objs = self.parse_objs_data(objs_data=objs_data)
                    try:
                        is_stopped = self.stop_device(device_id=dev_id)
                    except KeyError:
                        pass
                    # if is_stopped:
                    self.start_device(device_id=dev_id,
                                      objs=objs,
                                      upd_interval=upd_interval
                                      )
                else:
                    _log.warning('No objects from HTTP.')
                    # should we request obj faster?
            except Exception as e:
                _log.error(f'Update device error: {e}',
                           exc_info=True
                           )

    @abstractmethod
    def parse_objs_data(self, objs_data: dict[ObjType, list[dict]]
                        ) -> tuple[int, set[BACnetObj]]:
        """Extract objects data from response."""
        pass

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
            _log.warning(f"Device [{device_id}] isn't running. "
                         f"Please provide the id of the polling device: {e}"
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

        :return: Example: {200: '10.21.80.12:47808', ...}
        """
        return read_address_cache(address_cache_path=self.address_cache_path
                                  )

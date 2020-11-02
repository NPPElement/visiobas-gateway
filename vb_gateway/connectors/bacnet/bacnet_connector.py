import logging
from logging.handlers import RotatingFileHandler
from multiprocessing import SimpleQueue
from pathlib import Path
from threading import Thread
from time import sleep

import BAC0
from BAC0.core.io.IOExceptions import InitializationError
from aiohttp.web_exceptions import HTTPClientError, HTTPServerError

from vb_gateway.connectors.bacnet.device import BACnetDevice
from vb_gateway.connectors.bacnet.object_type import ObjType
from vb_gateway.connectors.bacnet.verifier import BACnetVerifier
from vb_gateway.connectors.base_connector import Connector


class BACnetConnector(Thread, Connector):
    def __init__(self, gateway, client_queue: SimpleQueue, config: dict):
        super().__init__()

        self.__logger = logging.getLogger(f'{self}')

        base_path = Path(__file__).resolve().parent.parent.parent
        log_path = base_path / f'logs/{__name__}.log'
        handler = RotatingFileHandler(filename=log_path,
                                      mode='a',
                                      maxBytes=50_000,
                                      encoding='utf-8'
                                      )
        self.__logger.addHandler(handler)

        self.setName(name=f'{self}-Thread')
        self.setDaemon(True)

        self.__gateway = gateway
        self.__client_queue = client_queue

        self.__config = config

        self.__connected = False
        self.__stopped = False

        self.__object_types_to_request = [
            ObjType.ANALOG_INPUT,
            ObjType.ANALOG_OUTPUT,
            ObjType.ANALOG_VALUE,

            ObjType.BINARY_INPUT,
            ObjType.BINARY_OUTPUT,
            ObjType.BINARY_VALUE,

            ObjType.MULTI_STATE_INPUT,
            ObjType.MULTI_STATE_OUTPUT,
            ObjType.MULTI_STATE_VALUE,
        ]

        self.__ready_devices_id = set()
        self.__polling_devices = {}

        # Match device_id with device_address. Example: {200: '10.21.80.12'}
        self.__address_cache = {}

        self.__network = None

        self.queue = SimpleQueue()
        self.__verifier = BACnetVerifier(bacnet_queue=self.queue,
                                         client_queue=client_queue,
                                         http_enable=True,
                                         mqtt_enable=False)

    def __repr__(self):
        return 'BACnetConnector'

    def run(self):
        self.__logger.info(f'{self} starting ...')

        self.__parse_address_cache()  # todo: Can the address_cache be updated?

        while not self.__stopped:
            if self.__network:  # IF HAVING INITIALIZED NETWORK
                sleep(1)  # for client login fixme!

                # devices_objects = {}
                try:  # Requesting objects and their types from the server
                    # FIXME: move to client
                    devices_objects = self.__gateway.get_devices_objects(
                        devices_id=list(self.__address_cache.keys()),
                        object_types=self.__object_types_to_request)
                    if devices_objects:  # If received devices with objects from the server
                        self.__logger.info('Received devices with '
                                           f'objects: {[*devices_objects.keys()]}'
                                           'Starting them ...')
                        self.start_devices(devices=devices_objects)
                    else:
                        self.__logger.error('No objects from server')
                        continue

                except (HTTPServerError, HTTPClientError) as e:
                    self.__logger.error('Error retrieving information about '
                                        f'devices objects from the server: {e}',
                                        exc_info=True)
                except OSError as e:
                    self.__logger.error(f'Please, check login: {e}')
                    # FIXME

                    # delay
                    sleep(60 * 60)

            else:  # IF NOT HAVE INITIALIZED BAC0 NETWORK
                self.__logger.info('BACnet network initializing ...')
                try:
                    # Initializing network for communication with BACnet Devices
                    self.__network = BAC0.lite()
                    BAC0.log_level('silence')  # fixme: no reaction - still having debug

                except InitializationError as e:
                    self.__logger.error(f'Network initialization error: {e}', exc_info=True)
                else:
                    self.__logger.info('Network initialized.')
        else:
            self.__network.disconnect()
            self.__logger.info('BAC0 Network disconnected.')
            self.__logger.info(f'{self} stopped.')

    def open(self):
        self.__connected = True
        self.__stopped = False
        self.start()

    def close(self) -> None:
        self.__stopped = True
        self.__connected = False

        self.__stop_devices()

        self.__verifier.close()
        self.__verifier.join()

    def start_devices(self, devices: dict) -> None:
        """ Starts BACnet Devices threads
        """
        for device_id, objects in devices.items():
            try:  # stop polling current device thread
                self.__polling_devices[device_id].stop_polling()
                self.__polling_devices[device_id].join()
                self.__polling_devices.pop(device_id)
            except KeyError:
                pass

            try:  # starting poll updated device
                self.__polling_devices[device_id] = BACnetDevice(
                    gateway=self.__gateway,
                    client_queue=self.__client_queue,
                    connector=self,
                    address=self.__address_cache[device_id],
                    device_id=device_id,
                    network=self.__network,
                    objects=objects
                )
            except Exception as e:
                self.__logger.error(f'Device [{device_id}] '
                                    f'starting error: {e}', exc_info=True)

    def __stop_devices(self) -> None:
        """ Stops BACnet Devices threads
        """
        try:
            for device in self.__polling_devices:
                device.stop_polling()
                device.join()
        except Exception as e:
            self.__logger.error(f'Device stopping error: {e}', exc_info=True)
        self.__logger.info('All devices were stopping.')

    def __parse_address_cache(self, address_cache_path: Path = None) -> None:
        """
        Parse text file format of address_cache.
        Add information about devices

        Example of file format:

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
        if (address_cache_path is None) or (not address_cache_path.is_file()):
            base_dir = Path(__file__).resolve().parent.parent.parent
            address_cache_path = base_dir / 'connectors/bacnet/address_cache'

        try:
            text = address_cache_path.read_text(encoding='utf-8')
        except FileNotFoundError as e:
            self.__logger.error(f"Not found address_cache file: {e}")
            raise e

        for line in text.split('\n'):
            trimmed = line.strip()
            if not trimmed.startswith(';') and trimmed:
                try:
                    device_id, mac, _, _, apdu = trimmed.split()
                except ValueError:
                    continue
                device_id = int(device_id)
                # In mac we have ip-address host:port
                mac = mac.split(':')
                address = '{}.{}.{}.{}:{}'.format(int(mac[0], base=16),
                                                  int(mac[1], base=16),
                                                  int(mac[2], base=16),
                                                  int(mac[3], base=16),
                                                  int(''.join((mac[4], mac[5])), base=16))
                self.__logger.debug(f"Device with id: '{device_id}' and "
                                    f"address: '{address}' was parsed from address_cache")
                self.__address_cache[device_id] = address

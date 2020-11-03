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
        LOGGER_FORMAT = '%(levelname)-8s [%(asctime)s] [%(threadName)s] %(name)s - (%(filename)s).%(funcName)s(%(lineno)d): %(message)s'
        formatter = logging.Formatter(LOGGER_FORMAT)
        handler.setFormatter(formatter)
        self.__logger.addHandler(handler)

        self.__config = config
        self.setName(name=f'{self}-Thread')
        self.setDaemon(True)

        self.__gateway = gateway
        self.__client_queue = client_queue

        self.__verifier_queue = SimpleQueue()
        self.__verifier = BACnetVerifier(bacnet_queue=self.__verifier_queue,
                                         client_queue=client_queue,
                                         http_enable=config['http_enable'],
                                         mqtt_enable=config['mqtt_enable'])

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

        self.__polling_devices = {}

        # Match device_id with device_address. Example: {200: '10.21.80.12'}
        self.__address_cache = {}

        self.__network = None

    def __repr__(self):
        return 'BACnetConnector'

    def run(self):
        self.__logger.info(f'{self} starting ...')

        while not self.__stopped:
            self.__update_address_cache(address_cache_path=None)

            if self.__network:  # IF HAVING INITIALIZED NETWORK
                try:  # Requesting objects and their types from the server
                    # FIXME: move to client
                    devices_objects = self.__gateway.get_devices_objects(
                        devices_id=list(self.__address_cache.keys()),
                        object_types=self.__object_types_to_request)

                    if devices_objects:  # If received devices with objects from the server
                        self.__logger.info('Received devices with '
                                           f'objects: {[*devices_objects.keys()]} '
                                           'Starting them ...')
                        self.start_devices(devices=devices_objects)
                    else:
                        self.__logger.error('No objects from server')
                        continue

                except (HTTPServerError, HTTPClientError) as e:
                    self.__logger.error('Error retrieving information about '
                                        f'devices objects from the server: {e}')
                except OSError as e:
                    self.__logger.error(f'Please, check login: {e}')
                    # FIXME

                # delay
                self.__logger.debug('Sleep 1h')
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
        self.__logger.debug('Stopping current devices ...')
        self.__stop_devices()

        for device_id, objects in devices.items():
            self.__logger.info(f'Starting device [{device_id}] ...')
            try:  # start polling device
                self.__polling_devices[device_id] = BACnetDevice(
                    gateway=self.__gateway,
                    verifier_queue=self.__verifier_queue,
                    connector=self,
                    address=self.__address_cache[device_id],
                    device_id=device_id,
                    network=self.__network,
                    objects=objects
                )
            except Exception as e:
                self.__logger.error(f'Device [{device_id}] '
                                    f'starting error: {e}', exc_info=True)
            else:
                self.__logger.info(f'Device [{device_id}] started')

    def __stop_devices(self) -> None:
        """ Stops BACnet Devices threads
        """
        try:
            # for device_id in self.__polling_devices.keys():
            #     self.__stop_device(device_id=device_id)

            [self.__stop_device(device_id=device_id) for device_id in
             self.__polling_devices.keys()]
            self.__polling_devices = {}

        except Exception as e:
            self.__logger.error(f'Stopping devices error: {e}', exc_info=True)
        else:
            self.__logger.info('BACnet devices were stopping')

    def __stop_device(self, device_id: int) -> None:
        """ Stops device by device_id
        """
        try:
            self.__logger.debug(f'Device [{device_id}] stopping polling ...')
            self.__polling_devices[device_id].stop_polling()
            self.__logger.debug(f'Device [{device_id}] stopped polling')
            self.__polling_devices[device_id].join()
            self.__logger.debug(f'Device [{device_id}]-Thread stopped')
            # del self.__polling_devices[device_id]
            # self.__logger.info(f'Device [{device_id}]-Thread removed')
        except KeyError as e:
            self.__logger.error(f'The device with id {device_id} is not running. '
                                f'Please provide the id of the polling device: {e}')
        except Exception as e:
            self.__logger.error(f'Device stopping error: {e}')

    def __update_address_cache(self, address_cache_path: Path = None) -> None:
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
        if (address_cache_path is None) or (not address_cache_path.is_file()):
            base_dir = Path(__file__).resolve().parent.parent.parent
            address_cache_path = base_dir / 'connectors/bacnet/address_cache'

        try:
            text = address_cache_path.read_text(encoding='utf-8')
        except FileNotFoundError as e:
            self.__logger.error(f"Not found address_cache file: {e}")
            raise e

        self.__address_cache = {}

        for line in text.split('\n'):
            trimmed = line.strip()
            if not trimmed.startswith(';') and trimmed:
                try:
                    device_id, mac, _, _, apdu = trimmed.split()
                except ValueError:
                    continue
                device_id = int(device_id)
                # In mac we have ip-address host:port in hex
                mac = mac.split(':')
                address = '{}.{}.{}.{}:{}'.format(int(mac[0], base=16),
                                                  int(mac[1], base=16),
                                                  int(mac[2], base=16),
                                                  int(mac[3], base=16),
                                                  int(''.join((mac[4], mac[5])), base=16))
                self.__logger.debug(f"Device with id: '{device_id}' and "
                                    f"address: '{address}' was parsed from address_cache")
                self.__address_cache[device_id] = address

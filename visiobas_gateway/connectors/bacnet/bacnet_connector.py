import asyncio
import logging
from pathlib import Path
from threading import Thread

import BAC0
from BAC0.core.io.IOExceptions import InitializationError
from aiohttp.web_exceptions import HTTPClientError, HTTPServerError

from visiobas_gateway.connectors.bacnet.bacnet_device import BACnetDevice
from visiobas_gateway.connectors.bacnet.object_type import ObjectType
from visiobas_gateway.connectors.connector import Connector


class BACnetConnector(Thread, Connector):
    def __init__(self, gateway, config: dict):
        super().__init__()

        self.__logger = logging.getLogger(f'{self}')
        self.setName(name=f'{self}-Thread')

        self.__gateway = gateway

        if config is not None:
            self.__config = config

        self.__connected = False
        self.__stopped = False

        self.__object_types_to_request = [
            ObjectType.ANALOG_INPUT,
            ObjectType.ANALOG_OUTPUT,
            ObjectType.ANALOG_VALUE,

            ObjectType.BINARY_INPUT,
            ObjectType.BINARY_OUTPUT,
            ObjectType.BINARY_VALUE,

            ObjectType.MULTI_STATE_INPUT,
            ObjectType.MULTI_STATE_OUTPUT,
            ObjectType.MULTI_STATE_VALUE,
        ]

        self.__ready_devices_id = set()
        self.__polling_devices = []

        # Match device_id with device_address. Example: {200: '10.21.80.12'}
        self.__address_cache = {}

        self.__network = None

    def __repr__(self):
        return 'BACnetConnector'

    def run(self):
        self.__logger.info(f'{self} starting ...')

        self.__parse_address_cache()  # todo: Can the address_cache be updated?

        while not self.__stopped:
            if not self.__network:
                self.__logger.info('BACnet network initializing')
                try:
                    self.__network = BAC0.lite()
                    BAC0.log_level('silence')  # fixme: no reaction - still having debug
                    # BAC0.device()
                    # self.__network.build_rp_request()

                except InitializationError as e:
                    self.__logger.error(f'Network initialization error: {e}', exc_info=True)
                else:
                    self.__logger.info('Network initialized.')

            else:  # IF HAVING INITIALIZED NETWORK
                # todo: implement circular request one time per hour
                asyncio.run(asyncio.sleep(0.5))  # for client login fixme!

                devices_objects = {}
                try:  # Requesting objects and their types from the server
                    # FIXME: write method for update
                    devices_objects.update(self.__gateway.get_devices_objects(
                        devices_id=list(self.__address_cache.keys()),
                        object_types=self.__object_types_to_request))
                except (HTTPServerError, HTTPClientError) as e:
                    self.__logger.error('Error retrieving information about '
                                        f'devices objects from the server: {e}',
                                        exc_info=True)

                if devices_objects:  # If received devices with objects from the server
                    self.__logger.info('Received devices with '
                                       f'objects: {[*devices_objects.keys()]}')

                    for device_id, objects in devices_objects.items():
                        try:  # polling all objects from the device
                            self.__polling_devices.append(
                                BACnetDevice(gateway=self.__gateway,
                                             address=self.__address_cache[device_id],
                                             device_id=device_id,
                                             network=self.__network,
                                             objects=objects)
                            )
                        except Exception as e:
                            self.__logger.error(f'Device [{device_id}] '
                                                f'error: {e}', exc_info=True)

                    # delay
                    asyncio.run(asyncio.sleep(3600))

                # todo: verify collected data

                else:
                    self.__logger.error('No objects from server')
                    continue
        else:
            self.__logger.info(f'{self} stopped.')

    def open(self):
        self.__connected = True
        self.__stopped = False
        self.start()

    def close(self) -> None:
        self.__stopped = True
        self.__connected = False

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
                device_id, mac, _, _, apdu = trimmed.split()
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

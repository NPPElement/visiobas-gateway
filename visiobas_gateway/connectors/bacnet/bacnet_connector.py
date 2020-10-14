import asyncio
import logging
from pathlib import Path
from threading import Thread

import BAC0
from BAC0.core.io.IOExceptions import InitializationError

from visiobas_gateway.connectors.bacnet.bacnet_verifier import BACnetVerifier
from visiobas_gateway.connectors.connector import Connector


class BACnetConnector(Thread, Connector):
    def __init__(self, gateway, config: dict):
        super().__init__()

        self.__logger = logging.getLogger('BACnetConnector')
        self.setName(name='BACnetConnector-Thread')

        self.__gateway = gateway

        if config is not None:
            self.__config = config

        self.__connected = False
        self.__stopped = False

        self.__verifier = BACnetVerifier()

        self.__object_types_to_request = [
            'analog-input',
            'analog-output',
            'analog-value',
            'binary-input',
            'binary-output',
            'binary-value',
            'multi-state-input',
            'multi-state-output',
            'multi-state-value',
            # 'notification-class'
        ]

        self.__ready_devices_id = set()
        self.__connected_devices_id = set()

        # Match device_id with device_address. Example: {200: '10.21.80.12'}
        self.__address_cache = {}

        self.__network = None

    def __str__(self):
        return 'BACnet connector'

    def run(self):
        self.__logger.info('Starting BACnet Connector')

        self.__parse_address_cache()  # todo: Can the address_cache be updated?

        while not self.__stopped:
            if not self.__network:
                self.__logger.info('BACnet network initializing')
                try:
                    self.__network = BAC0.lite()
                except InitializationError as e:
                    self.__logger.error(f'Network initialization error: {e}')
                else:
                    self.__logger.info('Network initialized.')

            else:  # IF HAVING INITIALIZED NETWORK
                try:
                    # Requesting objects and their types from the server
                    devices_objects = self.__gateway.get_devices_objects(
                        devices_id=list(self.__address_cache.keys()),
                        object_types=self.__object_types_to_request
                    )

                    # todo: Connect the received devices. Start polling
                    # self.__connect_addr_cache()

                    # if self.__ready_devices_id:
                    #     # self.__connect_devices()
                    #
                    # else:
                    #     self.__logger.debug('No ready devices for polling.')

                    # todo: verify collected data
                    # todo: send data to the gateway then to client
                except Exception as e:
                    self.__logger.error(f'Error: {e}')

            # delay
            asyncio.run(asyncio.sleep(10))

        else:
            self.__logger.info('BACnet connector stopped.')

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

    # def update_devices(self, devices: list) -> None:
    #     """
    #     :param devices: contains devices id
    #     """
    #     self.__devices_from_server.update(set(devices))
    #
    #     for device_id in devices:
    #         if device_id in self.__address_cache:
    #             self.__ready_devices_id.add(device_id)
    #         else:
    #             self.__logger.info("The address of the device with "
    #                                f"id '{device_id}' was not found.")

    def __connect_devices(self) -> None:
        """Connects devices to the network"""
        for device_id in self.__ready_devices_id:
            try:
                BAC0.device(address=self.__address_cache[device_id],
                            device_id=device_id,
                            network=self.__network,
                            poll=self.__config.get('poll_period', 10))
            except Exception as e:
                self.__logger.error(f'Device connection error: {e}')
            else:
                self.__logger.debug(f"Device with id '{device_id}' was connected")

    # def __connect_addr_cache(self):
    #     self.__logger.info('Connecting to devices from address_cache')
    #     for device_id in self.__address_cache.keys():
    #         try:
    #             device = BAC0.device(address=self.__address_cache[device_id],
    #                                  device_id=device_id,
    #                                  network=self.__network,
    #                                  poll=self.__config.get('poll_period', 10))
    #
    #             self.__logger.info(f'Device points: {device.points}')
    #         except Exception as e:
    #             self.__logger.error(f'Device_id: {device_id} connection error: {e}')
    #         else:
    #             self.__logger.debug(f"Device with id '{device_id}' was connected")

import logging
from pathlib import Path
from threading import Thread

import BAC0

from visiobas_gateway.connectors.bacnet.bacnet_verifier import BACnetVerifier
from visiobas_gateway.connectors.connector import Connector
from visiobas_gateway.gateway.visio_gateway import VisioGateway


class BACnetConnector(Thread, Connector):
    def __init__(self, gateway: VisioGateway, config: dict):
        super().__init__()

        self._logger = logging.getLogger('BACnetConnector')

        self._gateway = gateway

        if config is not None:
            self._config = config

        self._connected = False
        self._stopped = False

        self._verifier = BACnetVerifier()

        self._devices_from_server = set()  # contains bacnet devices id
        self._ready_devices_id = set()
        self._connected_devices_id = set()
        self._collected_data = []  # queue
        self._verified_data = []  # queue

        # Match device_id with device_address. Example: {200: '10.21.80.12'}
        self._address_cache = {}
        self._parse_address_cache()

        self.__network = None

    def __str__(self):
        return 'BACnet connector'

    def run(self):
        try:
            self.__network = BAC0.connect(ip=self._config['local_address'],
                                          port=self._config['port'],
                                          mask=self._config['mask'])
        except Exception as e:
            self._logger.error(f'Network initialization error: {e}')
        else:
            self._connected = True

        if self._ready_devices_id:
            self._connect_devices()
        else:
            self._logger.debug('No ready devices for polling.')

        while not self._stopped and self._connected:
            for device in self.__network.devices:
                # todo: implement poll period

                self._collected_data.append(
                    {'device_id': None,  # todo: get device_id
                     'data': device.lastValue,
                     'statusFlags': device.statusFlags
                     })
                # todo: verify collected data
                # todo: send data to the gateway then to client

    def open(self):
        self._connected = True
        self._stopped = False
        self.start()

    def close(self) -> None:
        self._stopped = True
        self._connected = False

    def _parse_address_cache(self, address_cache_path: Path = None) -> None:
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
        if address_cache_path is None:
            address_cache_path = Path.cwd() / 'address_cache'

        if address_cache_path.exists():
            text = address_cache_path.read_text()
        else:
            raise FileNotFoundError

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
                self._logger.debug(f"Device with id: '{device_id}' and "
                                   f"address: '{address}' was parsed from address_cache")
                self._address_cache[device_id] = address

    def update_devices(self, devices: list) -> None:
        """
        :param devices: contains devices id
        """
        self._devices_from_server.update(set(devices))

        for device_id in devices:
            if device_id in self._address_cache:
                self._ready_devices_id.add(device_id)
            else:
                self._logger.info("The address of the device with "
                                  f"id '{device_id}' was not found.")

    def _connect_devices(self) -> None:
        """Connects devices to the network"""
        for device_id in self._ready_devices_id:
            try:
                BAC0.device(address=self._address_cache[device_id],
                            device_id=device_id,
                            network=self.__network,
                            poll=self._config.get('poll_period', 10))
            except Exception as e:
                self._logger.error(f'Device connection error: {e}')
            else:
                self._logger.debug(f"Device with id '{device_id}' was connected")

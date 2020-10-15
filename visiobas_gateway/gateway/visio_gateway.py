import asyncio
import json
import logging
from pathlib import Path

from visiobas_gateway.connectors.bacnet.bacnet_connector import BACnetConnector
from visiobas_gateway.gateway.visio_client import VisioClient


class VisioGateway:
    def __init__(self, config_path: Path = None):

        self.__logger = logging.getLogger('VisioGateway')

        if (config_path is None) or (not config_path.is_file()):
            base_dir = Path(__file__).resolve().parent.parent
            config_path = base_dir / 'config/gateway.json'
        try:
            with open(config_path, mode='r', encoding='utf-8') as cfg_file:
                self._config = json.load(fp=cfg_file)
        except FileNotFoundError as e:
            self.__logger.error(f'Not found config file: {e}')
            raise e

        self.__stopped = False

        self.__client = None  # VisioClient(gateway=self, config=self._config['client'])

        self.__notifier = None
        self.__statistic = None

        self.__address_cache_devices_id = None

        self.__connectors = {
            'bacnet': BACnetConnector(
                gateway=self,
                config=self._config.get('bacnet_connector', None)),
            # 'modbus_tcp': None,
            # 'modbus_rtu': None,
            # 'knx_ip': None,
            # 'mqtt': None
            # etc. todo: not implemented
        }

        self.__logger.info('Starting VisioGateway.')
        try:
            self.__client = VisioClient(gateway=self, config=self._config['client'])
            self.__start_connectors()
        except Exception as e:
            self.__logger.error(f'Init error: {e}', exc_info=True)

        while not self.__stopped:
            try:
                pass

                # delay
                asyncio.run(asyncio.sleep(10))

            except Exception as e:
                self.__logger.error(f'Error: {e}', exc_info=True)
        else:
            self.__logger.info('VisioGateway stopped.')

    def __start_connectors(self) -> None:
        """Opens connection with all connectors"""
        for connector in self.__connectors.values():
            try:
                connector.open()
            except Exception as e:
                self.__logger.error(f'Connector opening error: {e}')
            else:
                self.__logger.info(f'Open: {connector}')
                self._connectors_connected = True

    def get_devices_objects(self, devices_id: list, object_types: list):
        """
        Called from the BACnet connector. Uses the VisioClient.

        :param devices_id:
        :param object_types:
        :return: dictionary with object types for each device
        """
        devices_objects = asyncio.run(
            self.__client.rq_devices_objects(devices_id=devices_id,
                                             object_types=object_types)
        )

        return devices_objects

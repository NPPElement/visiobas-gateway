import asyncio
import json
import logging
from multiprocessing import SimpleQueue
from pathlib import Path
from time import sleep

from vb_gateway.connectors.bacnet.bacnet_connector import BACnetConnector
from vb_gateway.gateway.http_client import VisioHTTPClient


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

        self.__client_bacnet_queue = SimpleQueue()
        self.__http_client = VisioHTTPClient(gateway=self,
                                             config=self._config['http_client'],
                                             bacnet_queue=self.__client_bacnet_queue)
        sleep(1)

        # self.__notifier = None  # todo
        # self.__statistic = None  # todo

        self.__address_cache_devices_id = None

        self.__connectors = {
            'bacnet': BACnetConnector(
                gateway=self,
                client_queue=self.__client_bacnet_queue,
                config=self._config.get('bacnet_connector', None)),
            # 'modbus_tcp': None,
            # 'modbus_rtu': None,
            # 'knx_ip': None,
            # 'mqtt': None
            # etc. todo
        }

        self.__logger.info(f'{self} starting ...')
        try:
            self.__start_connectors()
        except Exception as e:
            self.__logger.error(f'Init error: {e}', exc_info=True)

        while not self.__stopped:
            try:
                sleep(60 * 60)
            except (KeyboardInterrupt, SystemExit):
                self.__stop()
            except Exception as e:
                self.__logger.error(f'Error: {e}', exc_info=True)
        else:
            self.__logger.info(f'{self} stopped.')

    def __repr__(self):
        return 'VisioGateway'

    def __stop(self):
        self.__stop_connectors()

        self.__http_client.stop()
        self.__http_client.join()
        raise SystemExit

    def __start_connectors(self) -> None:
        """ Opens connection with all connectors
        """
        for connector in self.__connectors.values():
            try:
                connector.open()
            except Exception as e:
                self.__logger.error(f'{connector} opening error: {e}')

    def __stop_connectors(self) -> None:
        """ Closes connections with all connectors
        """
        for connector in self.__connectors.values():
            try:
                connector.close()
                connector.join()
            except Exception as e:
                self.__logger.error(f'{connector} closing error: {e}')

    def get_devices_objects(self, devices_id: list, object_types: list) -> dict:
        """
        Called from the BACnet connector. Uses the VisioClient.

        :param devices_id:
        :param object_types:
        :return: dictionary with object types for each device
        """

        # FIXME: CHANGE TO QUEUE, MOVE TO CLIENT
        devices_objects = asyncio.run(
            self.__http_client.rq_devices_objects(devices_id=devices_id,
                                                  object_types=object_types)
        )
        return devices_objects

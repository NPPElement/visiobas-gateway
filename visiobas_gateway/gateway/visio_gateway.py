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
            self.__logger.error(f"Not found config file: {e}")
            raise e

        self.__stopped = False

        self.__client = None  # VisioClient(gateway=self, config=self._config['client'])
        self.__data_for_connectors = {}

        self.__notifier = None
        self.__statistic = None

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
            self.__logger.error(f'Init error: {e}')

        while not self.__stopped:
            try:
                if self.__is_data_for_connectors():
                    self.__update_connectors()

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(asyncio.sleep(10))
                loop.close()

            except Exception as e:
                self.__logger.error(f'Error: {e}')

    def update_from_client(self, data: list):
        """Calls from client to update data from server."""
        # FIXME: NOW IT'S BACnet INFO

        self.__data_for_connectors['bacnet'] = [device['75'] for device in data]

    def __is_data_for_connectors(self) -> bool:
        return bool(self.__data_for_connectors)

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

    # def put_devices_to_connectors(self, devices_for_connectors: dict) -> None:
    #     """Sends information about devices to connectors"""
    #
    #     for protocol_name, devices in devices_for_connectors.items():
    #         try:
    #             self.__connectors[protocol_name].update_devices(devices=devices)
    #         except KeyError as e:
    #             self.__logger.error(f'Connector for {protocol_name} not implemented: {e}')
    #         except Exception as e:
    #             self.__logger.error(f'Error updating devices for '
    #                                 f'the connector {protocol_name}: {e}')

    def __update_connectors(self) -> None:
        # FIXME NOW ONLY BACNET CONNECTOR
        try:
            self.__connectors['bacnet'].update_devices(self.__data_for_connectors['bacnet'])
            self.__data_for_connectors = {}
        except Exception as e:
            self.__logger.error(f'Update connector error: {e}')

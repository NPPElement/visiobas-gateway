import asyncio
import json
import logging
from pathlib import Path

from visiobas_gateway.connectors.bacnet.bacnet_connector import BACnetConnector
from visiobas_gateway.gateway.visio_client import VisioClient


class VisioGateway:
    def __init__(self, config_path: Path = None):

        self._logger = logging.getLogger('VisioGateway')

        if (config_path is None) or (not config_path.is_file()):
            base_dir = Path(__file__).resolve().parent.parent
            config_path = base_dir / 'config/gateway.json'
        try:
            with open(config_path, mode='r', encoding='utf-8') as cfg_file:
                self._config = json.load(fp=cfg_file)
        except FileNotFoundError as e:
            self._logger.error(f"Not found config file: {e}")
            raise e

        self._stopped = False

        self._client = None  # VisioClient(gateway=self, config=self._config['client'])
        self._data_from_server = {}

        self._notifier = None
        self._statistic = None

        self._connectors = {
            'bacnet': BACnetConnector(
                gateway=self,
                config=self._config.get('bacnet_connector', None)),
            # 'modbus_tcp': None,
            # 'modbus_rtu': None,
            # 'knx_ip': None,
            # 'mqtt': None
            # etc. todo: not implemented
        }

        self._logger.info('Starting VisioGateway.')
        try:
            self._client = VisioClient(gateway=self, config=self._config['client'])

            while not self._stopped:
                if not self._client.is_connected():
                    pass
                    # todo: What should we do, if we not connected to server?
                    # todo: Should we call login in gateway?
                    # await self._client._rq_login()

                    # todo: What is the delay?

                if not self._data_from_server:
                    loop = asyncio.get_event_loop()
                    devices_for_connectors = loop.run_until_complete(
                        self._client.get_devices_for_connectors())
                    loop.close()
                    self._data_from_server.update(devices_for_connectors)
                    # todo: Should we refresh data from server? How often?

                self.put_devices_to_connectors(
                    devices_for_connectors=self._data_from_server)
                self._start_connectors()

        except Exception as e:  # fixme: exceptions
            self._logger.error(f'Error in VisioGateway: {e}')

    def update_info_from_server(self, devices_for_connectors: dict):
        """Calls from client to update data from server."""
        self._data_from_server.update(devices_for_connectors)

    def _start_connectors(self) -> None:
        """Opens connection with all connectors"""
        for connector in self._connectors.values():
            try:
                connector.open()
            except Exception as e:
                self._logger.error(f'Connector opening error: {e}')
            else:
                self._logger.info(f'Open: {connector}')

    def put_devices_to_connectors(self, devices_for_connectors: dict) -> None:
        """Sends information about devices to connectors"""

        for protocol_name, devices in devices_for_connectors.items():
            try:
                self._connectors[protocol_name].update_devices(devices=devices)
            except LookupError as e:
                self._logger.error(f'Connector for {protocol_name} not implemented: {e}')
            except Exception as e:
                self._logger.error(f'Error updating devices for '
                                   f'the connector {protocol_name}: {e}')

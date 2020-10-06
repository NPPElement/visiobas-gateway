import json
import logging
from pathlib import Path

from visiobas_gateway.connectors.bacnet.bacnet_connector import BACnetConnector
from visiobas_gateway.gateway.visio_client import VisioClient


class VisioGateway:
    def __init__(self, config_path: Path = None):

        self._logger = logging.getLogger('VisioGateway')

        if (config_path is None) or (not config_path.exists()):
            config_path = Path.cwd().parent / 'config' / 'gateway.json'
        with open(file=config_path, mode='r', encoding='utf-8') as cfg_file:
            self._config = json.load(fp=cfg_file)

        self._stopped = False

        self._client = None  # VisioClient(gateway=self, config=self._config['client'])
        self._notifier = None
        self._statistic = None

        self._connectors = {
            'bacnet': BACnetConnector(
                gateway=self,
                config=self._config.get('bacnet_connector', None)),
            'modbus_tcp': None,
            'modbus_rtu': None,
            'knx_ip': None,
            'mqtt': None
            # etc
        }

        try:
            self._client = VisioClient(gateway=self, config=self._config['client'])

            while not self._stopped:
                if not self._client.is_connected():
                    # todo: What should we do, if we not connected to server?
                    # await self._client._rq_login()
                    data = self._client.get_devices_id_by_protocol()
                    for protocol_name, devices in data.items():
                        connector = self._connectors.get(protocol_name, None)
                        connector.update_devices()



        except Exception as e:  # fixme: exceptions
            self._logger.error(f'Error in VisioGateway: {e}')


    def _add_devices_to_connector(self, protocol_name: str, devices_id: list) -> None:
        """
        :param protocol_name: to define a connector for adding devices
        :param devices_id: devices we want to add
        """
        protocol_devices_id = self.__devices_id.get(protocol_name, None)
        if protocol_devices_id:
            protocol_devices_id.extend(devices_id)

        connector = self._connectors.get(protocol_name, None)
        if connector:
            connector.update_devices(devices_id=devices_id)

    def _start_connectors(self) -> None:
        """
        Opens connection with all connectors
        """
        for connector in self._connectors.values():
            if connector:
                try:
                    connector.open()
                except Exception as e:
                    self._logger.error(f'Connector opening error: {e}')
                else:
                    self._logger.info(f'Open: {connector}')

    def get_devices_id_from_server(self) -> None:
        """
        Receives information about devices from the server and transmits it to connectors.
        """
        server_response = await self._client._rq_devices()
        server_devices_id = self._client.get_devices_id_by_protocol(
            server_response=server_response)

        # todo: make for all protocols
        bacnet_connector = self._connectors.get('bacnet', None)
        if bacnet_connector:
            bacnet_connector.update_devices(server_devices_id)

    def start_polling(self) -> None:
        """
        Call to start the gateway.
        """
        self._logger.info('Starting VisioGateway.')

        await self._client._rq_login()
        server_bacnet_devices_id = self.get_devices_id_from_server()

        # todo: for all protocols
        self._add_devices_to_connector(protocol_name='bacnet',
                                       devices_id=server_bacnet_devices_id)
        self._start_connectors()

        while not self._stopped:
            pass
            # transferring data from the connector to the server



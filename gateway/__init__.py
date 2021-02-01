from multiprocessing import SimpleQueue
from pathlib import Path
from time import sleep

from gateway.connectors.bacnet.bacnet_connector import BACnetConnector
from gateway.connectors.modbus.modbus_connector import ModbusConnector
from gateway.http_.client import VisioHTTPClient
from gateway.logs import get_file_logger
from gateway.verifier import BACnetVerifier

_base_path = Path(__file__).resolve().parent.parent

_log = get_file_logger(logger_name=__name__,
                       size_bytes=50_000_000
                       )


class VisioGateway:
    delay_loop = 60 * 60

    def __init__(self, config: dict):
        self._config = config  # todo check cfg
        self._stopped = False

        # todo: refactor
        self._protocol_verifier_queue = SimpleQueue()
        self._verifier_http_queue = SimpleQueue()

        self._http_bacnet_queue = SimpleQueue()
        self._http_modbus_queue = SimpleQueue()

        self.connectors = {
            'bacnet': BACnetConnector(
                gateway=self,
                http_queue=self._http_bacnet_queue,
                verifier_queue=self._protocol_verifier_queue,
                config=self._config['bacnet']),
            'modbus': ModbusConnector(
                gateway=self,
                http_queue=self._http_modbus_queue,
                verifier_queue=self._protocol_verifier_queue,
                config=self._config['modbus']
            ),
            # 'xml': None
            # 'modbus_rtu': None,
            # 'knx_ip': None,
            # 'mqtt': None
            # etc. todo
        }

        self.http_client = VisioHTTPClient.create_from_yaml(
            gateway=self,
            verifier_queue=self._verifier_http_queue,
            cfg_path=_base_path / 'config/http.yaml'
        )

        self.verifier = BACnetVerifier(protocols_queue=self._protocol_verifier_queue,
                                       http_queue=self._verifier_http_queue,
                                       config=self._config['bacnet_verifier']
                                       )
        # self.mqtt_client =

        # self.__notifier = None  # todo
        # self.__statistic = None  # todo
        self.http_client.start()
        sleep(1)
        self.verifier.start()

        self.run_forever()

    def run_forever(self):
        _log.info(f'{self} starting ...')
        try:
            self._start_connectors()
        except Exception as e:
            _log.error(f'Start connectors error: {e}',
                       exc_info=True
                       )

        while not self._stopped:
            try:
                sleep(self.delay_loop)
            except (KeyboardInterrupt, SystemExit):
                self._stop()
            except Exception as e:
                _log.error(f'Error: {e}',
                           exc_info=True
                           )
        else:
            _log.info(f'{self} stopped.')

    def __repr__(self):
        return 'VisioGateway'

    def _stop(self):
        _log.warning('Stopping ...')
        self._stop_connectors()

        self.verifier.close()
        self.verifier.join()

        self.http_client.stop()
        self.http_client.join()

        self._stopped = True

    def _start_connectors(self) -> None:
        """ Opens connection with connectors."""
        for connector in self.connectors.values():
            try:
                connector.open()
            except Exception as e:
                _log.error(f'{connector} opening error: {e}',
                           exc_info=True
                           )

    def _stop_connectors(self) -> None:
        """ Close connections with connectors."""
        for connector in self.connectors.values():
            try:
                connector.close()
                connector.join()
            except Exception as e:
                _log.error(f'{connector} closing error: {e}',
                           exc_info=True
                           )

    def stop_devices(self) -> None:
        """Stop devices for all connectors."""
        for connector in self.connectors.values():
            try:
                # stop all polling devices
                connector.stop_devices(devices_id=connector.polling_devices.keys())
            except Exception as e:
                _log.error(f'{connector} stopping devices error: {e}',
                           exc_info=True
                           )

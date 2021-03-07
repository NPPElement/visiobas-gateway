# import atexit
from logging import getLogger
from multiprocessing import SimpleQueue
from pathlib import Path

from aiomisc import entrypoint

from gateway.api import VisioGatewayApiService
from gateway.clients import VisioHTTPClient, VisioMQTTClient
from gateway.connectors import BACnetConnector, ModbusConnector
from gateway.verifier import BACnetVerifier

_base_path = Path(__file__).resolve().parent

_log = getLogger(__name__)


class VisioGateway:
    def __init__(self, config: dict):
        self._config = config
        self._stopped = False

        self._protocol_verifier_queue = SimpleQueue()
        self._verifier_http_queue = SimpleQueue()
        self._verifier_mqtt_queue = SimpleQueue()

        self._http_bacnet_queue = SimpleQueue()
        self._http_modbus_queue = SimpleQueue()

        # Device updates in connectors are HTTP client initiated.
        # Connectors are not closed on update.
        # Therefore, they are created once when the gateway is created.
        self.connectors = {
            'bacnet': BACnetConnector(gateway=self,
                                      getting_queue=self._http_bacnet_queue,
                                      verifier_queue=self._protocol_verifier_queue,
                                      config=self._config['connector']['bacnet']
                                      ),
            'modbus': ModbusConnector(gateway=self,
                                      getting_queue=self._http_modbus_queue,
                                      verifier_queue=self._protocol_verifier_queue,
                                      config=self._config['connector']['modbus']
                                      ),
            # 'xml': None
            # 'modbus_rtu': None,
            # 'knx_ip': None,
            # 'mqtt': None
            # etc.
        }
        # Open connectors
        [connector.open() for connector in self.connectors.values()]

        # HTTP client updatable. Re-created inside the main loop
        # self.http_client = None

        self.mqtt_client = VisioMQTTClient.from_yaml(
            gateway=self,
            getting_queue=self._verifier_mqtt_queue,
            yaml_path=_base_path / 'config/mqtt.yaml'
        )
        self.mqtt_client.start()

        # The verifier does not need to be updated, so
        # it runs once when the gateway starts.
        self.verifier = BACnetVerifier(protocols_queue=self._protocol_verifier_queue,
                                       http_queue=self._verifier_http_queue,
                                       mqtt_queue=self._verifier_mqtt_queue,
                                       config=self._config['verifier']
                                       )
        self.verifier.start()

        self.http_client = VisioHTTPClient.from_yaml(
            gateway=self,
            getting_queue=self._verifier_http_queue,
            yaml_path=_base_path / 'config/http.yaml'
        )
        self.http_client.start()

        services = (
            VisioGatewayApiService(gateway=self,
                                   host=self._config['api'].get('host', 'localhost'),
                                   port=self._config['api'].get('port', 7070)
                                   ),
        )

        with entrypoint(*services) as loop:
            loop.run_forever()

        # self.__notifier = None  # todo
        # self.__statistic = None  # todo

        # self.run_main_loop()
        # sleep(40)

    def __repr__(self) -> str:
        return self.__class__.__name__

    @classmethod
    def from_yaml(cls, yaml_path: Path):
        """Create gateway with configuration, read from YAML file."""
        import yaml

        with yaml_path.open() as cfg_file:
            cfg = yaml.load(cfg_file, Loader=yaml.FullLoader)
        return cls(config=cfg)

    # def run_main_loop(self):
    #     """Main loop of gateway."""
    #     _log.info(f'{self} starting ...')
    #
    #     while not self._stopped:
    #         try:
    #             self.http_client = VisioHTTPClient.create_from_yaml(
    #                 gateway=self,
    #                 getting_queue=self._verifier_http_queue,
    #                 yaml_path=_base_path / 'config/http.yaml'
    #             )
    #             self.http_client.start()
    #
    #             update_period = self._config['gateway'].get('update_period', 60 * 60)
    #             _log.info(f'{self} sleep: {update_period} sec ...')
    #             sleep(update_period)
    #             self.http_client.stop()
    #
    #         except (KeyboardInterrupt, SystemExit, Exception) as e:
    #             self._stop()
    #             _log.error(f'Error: {e}',
    #                        exc_info=True
    #                        )
    #     else:
    #         _log.info(f'{self} stopped.')

    # @atexit.register
    def _stop(self):
        """Stop gateway modules in right order."""
        _log.warning('Stopping ...')
        self._stop_connectors()

        self.verifier.close()
        self.verifier.join()

        # self.http_client.stop()
        # self.http_client.join()

        self._stopped = True

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

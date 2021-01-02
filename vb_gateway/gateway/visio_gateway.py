from logging import getLogger
from multiprocessing import SimpleQueue
from time import sleep

from vb_gateway.connectors.bacnet.bacnet_connector import BACnetConnector
from vb_gateway.connectors.modbus.modbus_connector import ModbusConnector
from vb_gateway.gateway.http_client import VisioHTTPClient
from vb_gateway.gateway.verifier import BACnetVerifier


class VisioGateway:
    def __init__(self, config: dict):

        self.__logger = getLogger('VisioGateway')
        self.__config = config
        self.__stopped = False

        # todo: refactor
        self.__protocol_verifier_queue = SimpleQueue()
        self.__verifier_http_queue = SimpleQueue()

        self.http_client = VisioHTTPClient(gateway=self,
                                           config=self.__config['http'],
                                           verifier_queue=self.__verifier_http_queue)
        # self.__mqtt_broker = VisioMQTTBroker()
        sleep(1)

        # self.__notifier = None  # todo
        # self.__statistic = None  # todo

        # todo check cfg

        self.__verifier = BACnetVerifier(protocols_queue=self.__protocol_verifier_queue,
                                         http_queue=self.__verifier_http_queue,
                                         config=self.__config['bacnet_verifier'])

        self.__connectors = {
            'bacnet': BACnetConnector(
                gateway=self,
                verifier_queue=self.__protocol_verifier_queue,
                config=self.__config['bacnet']),
            'modbus': ModbusConnector(
                gateway=self,
                verifier_queue=self.__protocol_verifier_queue,
                config=self.__config['modbus']
            ),
            # 'xml': None
            # 'modbus_rtu': None,
            # 'knx_ip': None,
            # 'mqtt': None
            # etc. todo
        }

        self.__logger.info(f'{self} starting ...')
        try:
            self.__start_connectors()
        except Exception as e:
            self.__logger.error(f'Start connectors error: {e}', exc_info=True)

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
        self.__logger.warning('Stopping ...')
        self.__stop_connectors()

        self.__verifier.close()
        self.__verifier.join()

        self.http_client.stop()
        self.http_client.join()

        self.__stopped = True

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

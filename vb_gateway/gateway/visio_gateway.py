from json import load
from logging import getLogger
from multiprocessing import SimpleQueue
from pathlib import Path
from time import sleep

from vb_gateway.connectors.bacnet.bacnet_connector import BACnetConnector
from vb_gateway.connectors.modbus.modbus_connector import ModbusConnector
from vb_gateway.gateway.http_client import VisioHTTPClient
from vb_gateway.gateway.verifier import BACnetVerifier


class VisioGateway:
    def __init__(self, config_path: Path = None):

        self.__logger = getLogger('VisioGateway')

        if (config_path is None) or (not config_path.is_file()):
            base_dir = Path(__file__).resolve().parent.parent
            config_path = base_dir / 'config/gateway.json'
        try:
            with open(config_path, mode='r', encoding='utf-8') as cfg_file:
                self.__config = load(fp=cfg_file)
        except FileNotFoundError as e:
            self.__logger.error(f'Not found config file: {e}')
            raise e

        self.__stopped = False

        # todo: refactor
        # self.__http_bacnet_queue = SimpleQueue()
        # self.__http_modbus_queue = SimpleQueue()
        self.__protocol_verifier_queue = SimpleQueue()
        self.__verifier_http_queue = SimpleQueue()

        self.http_client = VisioHTTPClient(gateway=self,
                                           config=self.__config['http_client'],
                                           verifier_queue=self.__verifier_http_queue)
        # self.__mqtt_broker = VisioMQTTBroker()
        sleep(1)

        # self.__notifier = None  # todo
        # self.__statistic = None  # todo

        self.__verifier = BACnetVerifier(protocols_queue=self.__protocol_verifier_queue,
                                         http_queue=self.__verifier_http_queue,
                                         http_enable=self.__config['bacnet_verifier'][
                                             'http_enable'],
                                         mqtt_enable=self.__config['bacnet_verifier'][
                                             'mqtt_enable'])

        self.__connectors = {
            'bacnet': BACnetConnector(
                gateway=self,
                verifier_queue=self.__protocol_verifier_queue,
                # client_queue=self.__client_protocol_queue,
                config=self.__config.get('bacnet_connector', None)),
            'modbus': ModbusConnector(
                gateway=self,
                verifier_queue=self.__protocol_verifier_queue,
                # client_queue=self.__client_modbus_queue,
                config=self.__config.get('modbus_connector', None)
            ),
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

        self.http_client.stop()
        self.http_client.join()
        # raise SystemExit

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

    # def get_devices_objects(self, devices_id: list, object_types: list) -> dict:
    #     """
    #     Called from the BACnet connector. Uses the VisioClient.
    #
    #     :param devices_id:
    #     :param object_types:
    #     :return: dictionary with object types for each device
    #     """
    #
    #     # FIXME: CHANGE TO QUEUE, MOVE TO CLIENT
    #     devices_objects = asyncio.run(
    #         self.http_client.rq_devices_objects(devices_id=devices_id,
    #                                             obj_types=object_types)
    #     )
    #     return devices_objects

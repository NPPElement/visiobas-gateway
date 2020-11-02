import asyncio
import logging
from logging.handlers import RotatingFileHandler
from multiprocessing import SimpleQueue
from pathlib import Path
from threading import Thread

import aiohttp
from aiohttp import ClientResponse, ClientConnectorError

from vb_gateway.connectors.bacnet.object_property import ObjProperty
from vb_gateway.connectors.bacnet.object_type import ObjType


class VisioHTTPClient(Thread):
    def __init__(self, gateway, bacnet_queue: SimpleQueue, config: dict):
        super().__init__()

        self.__logger = logging.getLogger(f'{self}')

        base_path = Path(__file__).resolve().parent.parent
        log_path = base_path / f'logs/{__name__}.log'
        handler = RotatingFileHandler(filename=log_path,
                                      mode='a',
                                      maxBytes=50_000,
                                      encoding='utf-8'
                                      )
        LOGGER_FORMAT = '%(levelname)-8s [%(asctime)s] [%(threadName)s] %(name)s - (%(filename)s).%(funcName)s(%(lineno)d): %(message)s'
        formatter = logging.Formatter(LOGGER_FORMAT)
        handler.setFormatter(formatter)
        self.__logger.addHandler(handler)

        self.setName(name=f'{self}-Thread')
        self.setDaemon(True)

        self.__gateway = gateway
        self.__bacnet_queue = bacnet_queue

        if isinstance(config, dict):
            self.__config = config
        else:
            raise ValueError(f'Config for {self} not found.')

        self.__host = config['host-mirror']  # FIXME: prod
        # self.__host = config['host3']  # FIXME: test
        self.__port = config['port']

        self.__verify = config['ssl_verify']
        self.__login = config['auth']['login']
        self.__md5_pwd = config['auth']['pwd']

        # self.__session = None
        self.__connected = False
        self.__stopped = False

        # getting this data after login
        self.__user_id = None
        self.__bearer_token = None
        self.__auth_user_id = None

        self.__logger.info(f'{self} starting ...')
        self.start()

    def run(self) -> None:
        """
        Keeps the connection to the server. Login if necessary.
        Periodically requests updates from the server.
            Sends information received from the server to the gateway.
        """
        while not self.__stopped:
            if self.__connected:  # IF LOGGED IN
                try:
                    device_id, device_str = self.__bacnet_queue.get()
                    self.__rq_post_device(device_id=device_id, data=device_str)
                except Exception as e:
                    self.__logger.error(f"Receive'n'post device error: {e}", exc_info=True)

            else:  # IF NOT AUTHORIZED
                try:
                    asyncio.run(self.__rq_login())
                except ClientConnectorError as e:
                    self.__logger.error(f'Login error: {e}')  # , exc_info=True)
                else:
                    self.__connected = True
                    self.__logger.info('Successfully log in to the server.')
        else:
            self.__logger.info(f'{self} stopped.')

    def __repr__(self):
        return 'VisioClient'

    def is_connected(self) -> bool:
        return self.__connected

    def stop(self) -> None:
        self.__stopped = True
        self.__logger.info(f'{self} was stopped.')

    @property
    def __address(self) -> str:
        return ':'.join((self.__host, str(self.__port)))

    @property
    def __auth_headers(self) -> dict:
        headers = {
            'Authorization': f'Bearer {self.__bearer_token}'
        }
        return headers

    async def __rq_login(self) -> None:
        self.__logger.info('Logging in to the server ...')
        url = f'{self.__address}/auth/rest/login'
        data = {
            'login': self.__login,
            'password': self.__md5_pwd
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url=url, json=data) as response:
                self.__logger.debug(f'POST: {url}')
                data = await self.__extract_response_data(response=response)
                try:
                    self.__bearer_token = data['token']
                    self.__user_id = data['user_id']
                    self.__auth_user_id = data['auth_user_id']
                except TypeError as e:
                    self.__logger.error(f'Login Error! Please check login/password: {e}')
                # except OSError as e:
                #     self.__logger.error(f'Login Error! Please check server availability: {e}')

    # async def __rq_devices(self) -> dict:
    #     """
    #     Request of all available devices from server
    #     :return: data received from the server
    #     """
    #     self.__logger.debug('Requesting information about devices from the server ...')
    #
    #     url = f'{self.__address}/vbas/gate/getDevices'
    #
    #     async with aiohttp.ClientSession(headers=self.__auth_headers) as session:
    #         async with session.get(url=url) as response:
    #             self.__logger.debug(f'GET: {url}')
    #             data = await self.__extract_response_data(response=response)
    #             return data

    async def __rq_post_device(self, device_id: int, data) -> list:
        """
        Sends the polled information about the device to the server.
        Now only inform about rejected devices.

        :param device_id:
        :param data:
        :return: list of objects id, rejected by server side.
        """

        self.__logger.debug(f'Sending collected data about device [{device_id}]')

        url = f'{self.__address}/vbas/gate/light/{device_id}'

        async with aiohttp.ClientSession(headers=self.__auth_headers) as session:
            async with session.post(url=url, data=data) as response:
                self.__logger.info(f'POST: {url}')
                self.__logger.info(f'Body: {data}')
                data = await self.__extract_response_data(response=response)
                await self.__check_rejected(device_id=device_id,
                                            data=data)
                return data

    async def __check_rejected(self, device_id: int, data: list) -> list:
        """
        Inform about rejected objects.

        # todo: Now the server does not always correctly return the list with errors.

        :param data: polled by BACnet Device
        :return: list of rejected by server side.
        """
        if not data:  # all object are accepted on server side
            self.__logger.info(f'POST-result: Device [{device_id}] '
                               'Server didn\'t return unaccepted objects.')
            return data
        else:
            rejected_objects_id = [obj[str(ObjProperty.objectIdentifier.id)] for obj in
                                   data]
            self.__logger.warning(f'POST-result: Device [{device_id}] '
                                  'Error processing objects on '
                                  f'the server: {rejected_objects_id}')
            # todo: What should we doing with rejected objects?
            return rejected_objects_id

    async def __rq_device_object(self, device_id: int, object_type: ObjType) -> list:
        """
        Request of all available objects by device_id and object_type
        :param device_id:
        :param object_type:
        :return: data received from the server
        """
        self.__logger.debug(f"Requesting information about device [{device_id}], "
                            f"object_type: {object_type.name_dashed} from the server ...")

        url = f'{self.__address}/vbas/gate/get/{device_id}/{object_type.name_dashed}'

        async with aiohttp.ClientSession(headers=self.__auth_headers) as session:
            async with session.get(url=url) as response:
                self.__logger.debug(f'GET: {url}')
                data = await self.__extract_response_data(response=response)
                return data

    async def __rq_objects_for_device(self, device_id: int, object_types: list) -> dict:
        """
        Requests types of objects by device_id

        :param device_id:
        :param object_types:
        :return: Dictionary, where the key is the id of type of the objects,
        and the value is the list of id of objects of this type
        """

        # Create list with requests
        objects_requests = [self.__rq_device_object(device_id=device_id,
                                                    object_type=object_type) for
                            object_type in object_types]

        # From each response, if it's not empty, getting the id of objects.
        # Creating a dictionary, where the key is the type of the objects,
        # and the value is the list of tuples with id and name of objects of this type.
        device_objects = {
            object_type: [(prop[str(ObjProperty.objectIdentifier.id)],
                           prop[str(ObjProperty.objectName.id)]) for
                          prop in objects] for
            object_type, objects in
            zip(object_types, await asyncio.gather(*objects_requests))
            if objects
        }

        self.__logger.debug(f'For device_id: {device_id} '
                            f'received objects: {device_objects}')
        return device_objects

    async def rq_devices_objects(self, devices_id: list, object_types: list) -> dict:
        """
        Requests types of objects for each device_id.
        For each device creates a dictionary, where the key is object_type,
        and the value is a list of object identifiers.

        :param object_types:
        :param devices_id:
        :return: dictionary with object types for each device
        """

        # Create list with requests

        devices_requests = [self.__rq_objects_for_device(device_id=device_id,
                                                         object_types=object_types) for
                            device_id in devices_id]

        # Creating a dictionary, where the key is the device_id,
        # and the value is the dictionary, where the key is the object type,
        # and the value is the list of id of objects of this type.
        devices = {device_id: device_objects for device_id, device_objects in
                   zip(devices_id, await asyncio.gather(*devices_requests))
                   if device_objects}

        # todo: What should we do with devices with no objects?
        #  Now drops devices with no objects
        return devices

    async def __extract_response_data(self, response: ClientResponse) -> list or dict:
        """
        Checks the correctness of the response.
        :param response: server's response
        :return: response['data'] field
        """
        if response.status == 200:
            resp_json = await response.json()
            if resp_json['success']:
                self.__logger.debug('Received information from the server.')
                return resp_json['data']
            else:
                self.__logger.warning('Server returned failure response.')
                self.__logger.info(f'{resp_json}')
                # raise HTTPServerError
        else:
            self.__logger.warning(f'Server response status error: {response.status}')
            # raise HTTPClientError

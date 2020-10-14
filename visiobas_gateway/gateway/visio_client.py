import asyncio
import logging
from threading import Thread

import aiohttp
from aiohttp import ClientResponse

from visiobas_gateway.gateway.exceptions import LogInError


class VisioClient(Thread):
    def __init__(self, gateway, config: dict):
        super().__init__()

        self.__logger = logging.getLogger('VisioClient')
        self.setName(name='VisioClient-Thread')

        self.__gateway = gateway

        if isinstance(config, dict):
            self.__config = config
        else:
            raise ValueError(f'Config for VisioClient not found.')

        self.__host = config['test_host']  # FIXME: test/prod
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

        self.start()

    def run(self) -> None:
        """
        Keeps the connection to the server. Login if necessary.
        Periodically requests updates from the server.
            Sends information received from the server to the gateway.

        # TODO: Periodically sends the information received from the gateway to the server.
        """
        self.__logger.info('Starting VisioClient.')
        while not self.__stopped:
            if not self.__connected:  # LOGIN
                try:
                    asyncio.run(self.__rq_login())
                except ConnectionRefusedError as e:
                    self.__logger.error(f'Login error: {e}')
                except LogInError as e:
                    self.__logger.error(f'Login error: {e}')
                else:
                    self.__connected = True
                    self.__logger.info('Successfully log in to the server.')

            else:  # IF AUTHORIZED
                pass
                # TODO: send data to server

            # delay
            asyncio.run(asyncio.sleep(10))

        else:
            self.__logger.info('VisioClient stopped.')

    def is_connected(self) -> bool:
        return self.__connected

    def stop(self) -> None:
        self.__stopped = True
        self.__logger.info('VisioClient was stopped.')

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
                self.__logger.info(f'POST: {url}')
                data = await self.__extract_response_data(response=response)

                self.__bearer_token = data['token']
                self.__user_id = data['user_id']
                self.__auth_user_id = data['auth_user_id']

    async def __rq_devices(self) -> dict:
        """
        Request of all available devices from server
        # todo: Now only bacnet devices.
        :return: data received from the server
        """
        self.__logger.debug('Requesting information about devices from the server ...')

        url = f'{self.__address}/vbas/gate/getDevices'

        async with aiohttp.ClientSession(headers=self.__auth_headers) as session:
            async with session.get(url=url) as response:
                self.__logger.debug(f'GET: {url}')
                data = await self.__extract_response_data(response=response)
                return data

    async def __rq_device_object(self, device_id, object_type) -> list:
        """
        Request of all available objects by device_id and object_type
        :param device_id:
        :param object_type:
        :return: data received from the server
        """
        self.__logger.debug(f"Requesting information about device_id: {device_id}, "
                            f"object_type: {object_type} from the server ...")

        url = f'{self.__address}/vbas/gate/get/{device_id}/{object_type}'

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
        :return: Dictionary, where the key is the type of the objects,
        and the value is the list of id of objects of this type
        """

        # Create list with requests
        objects_requests = [self.__rq_device_object(device_id=device_id,
                                                    object_type=object_type) for
                            object_type in object_types]

        # From each response, if it's not empty, getting the id of objects.
        # Creating a dictionary, where the key is the type of the objects,
        # and the value is the list of id of objects of this type.
        device_objects = {object_type: [prop['75'] for prop in objects] for
                          object_type, objects in
                          zip(object_types, await asyncio.gather(*objects_requests))
                          if objects}

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
                   zip(devices_id, await asyncio.gather(*devices_requests))}

        # todo: What should we do with devices with no objects?
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
        else:
            self.__logger.warning(f'Server response status error: {response.status}')

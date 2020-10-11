import asyncio
import logging
from threading import Thread

import aiohttp
import requests

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

        self.__data_to_server = []

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
            if not self.__connected:
                try:
                    self.__rq_login()
                except ConnectionRefusedError as e:
                    self.__logger.error(f'Login error: {e}')
                except LogInError as e:
                    self.__logger.error(f'Login error: {e}')
                else:
                    self.__connected = True
                    self.__logger.info('Successfully log in to the server.')

            else:
                try:  # todo: What is the period?
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    data = loop.run_until_complete(
                        self.__rq_devices())
                    loop.close()

                    self.__gateway.update_from_client(data=data)

                except Exception as e:
                    self.__logger.error('Error retrieving information about '
                                        f'devices from the server: {e}')

                if self.__is_data_for_server():
                    pass
                    # TODO: send data to server

            # delay
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(asyncio.sleep(10))
            loop.close()

        else:
            self.__logger.info('VisioClient stopped.')

    @property
    def address(self) -> str:
        return ':'.join((self.__host, str(self.__port)))

    def is_connected(self) -> bool:
        return self.__connected

    def stop(self) -> None:
        self.__stopped = True
        self.__logger.info('VisioClient stopped')

    def __is_data_for_server(self) -> bool:
        return False
        # TODO: implement

    def __rq_login(self) -> None:
        self.__logger.info('Logging in to the server ...')
        url = f'{self.address}/auth/rest/login'
        data = {
            'login': self.__login,
            'password': self.__md5_pwd
        }
        with requests.Session() as session:
            self.__logger.info(f'POST: {url}')
            response = session.post(url=url, json=data)

            if response.status_code == 200:
                resp = response.json()
                if resp['success']:
                    self.__bearer_token = resp['data']['token']
                    self.__user_id = resp['data']['user_id']
                    self.__auth_user_id = resp['data']['auth_user_id']
                else:
                    self.__logger.info('Server returned failure response.')
                    raise LogInError
            else:
                self.__logger.info(f'Server response status error: {response.status_code}')
                raise LogInError

    async def __rq_devices(self) -> dict:
        """
        Request of all available devices from server
        # todo: Now only bacnet devices.
        :return: data received from the server
        """
        self.__logger.info('Requesting information about devices from the server ...')

        url = f'{self.address}/vbas/gate/getDevices'
        headers = {
            'Authorization': f'Bearer {self.__bearer_token}'
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url=url) as response:
                self.__logger.debug(f'GET: {url}')

                if response.status == 200:
                    resp = await response.json()
                    if resp['success']:
                        self.__logger.info('Received information about '
                                           'devices from the server.')
                        return resp['data']
                    else:
                        self.__logger.info('Server returned failure response.')
                else:
                    self.__logger.info(f'Server response status error: {response.status}')

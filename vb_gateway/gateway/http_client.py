import asyncio
from multiprocessing import SimpleQueue
from pathlib import Path
from threading import Thread
from time import sleep

from aiohttp import ClientResponse, ClientConnectorError, ClientSession, ClientError

from vb_gateway.connectors.bacnet.obj_property import ObjProperty
from vb_gateway.connectors.bacnet.obj_type import ObjType
from vb_gateway.utility.utility import get_file_logger


class VisioHTTPClient(Thread):
    def __init__(self, gateway, verifier_queue: SimpleQueue, config: dict):
        super().__init__()

        base_path = Path(__file__).resolve().parent.parent
        log_file_path = base_path / f'logs/{__name__}.log'

        self.__logger = get_file_logger(logger_name=f'{self}',
                                        file_size_bytes=50_000_000,
                                        file_path=log_file_path)

        self.setName(name=f'{self}-Thread')
        self.setDaemon(True)

        self.__gateway = gateway
        self.__verifier_queue = verifier_queue

        self.__config = config

        self.__get_host: str = config['get_host']
        self.__post_hosts: list[str] = config['post_hosts']
        self.__port = config['port']

        self.loop = asyncio.get_event_loop()
        self.loop.set_debug(enabled=True)

        self.__login: str = config['auth']['login']
        self.__password: str = config['auth']['password']

        # getting this data after login
        self.__user_id = self.__bearer_token = self.__auth_user_id = None
        self.__user_id = self.__bearer_token = self.__auth_user_id = self.login(
            login=self.__login,
            password=self.__password)

        # self.session = None

        self.session = ClientSession(headers=self.__auth_headers, loop=self.loop)

        self.__stopped = False

        self.start()

    @property
    def get_url(self) -> str:
        return 'http://' + ':'.join((self.__get_host, str(self.__port)))

    @property
    def post_urls(self) -> list[str, ...]:
        return ['http://' + ':'.join((post_host, self.__port))
                for post_host in self.__post_hosts]

    def run(self) -> None:
        self.__logger.info(f'{self} starting ...')

        while not self.__stopped:
            # self.listen_verifier()
            asyncio.run(self.listen_verifier())
        else:
            self.session.close()
            self.loop.close()
            self.__logger.info(f'{self} stopped')

    def listen_verifier(self):
        """ Keep the session. Sends data from connectors"""
        while not self.session.closed:
            try:
                self.__logger.warning('wait queue.get()')
                device_id, device_str = self.__verifier_queue.get()
                self.__logger.warning('Received data from BACnetVerifier: '
                                    f'Device[{device_id}]')

                # fire and forget
                self.loop.create_task(
                    self.rq_post_device(session=self.session,
                                        device_id=device_id,
                                        data=device_str),
                    name=f'POST[{device_id}]')
            except ClientError as e:
                self.__logger.warning(
                    f'Cannot send data about device [{device_id}] because '
                    f'connection problem: {e}')
                # todo: implement second attempt?
            except Exception as e:
                self.__logger.error(f'Receive and post device error: {e}',
                                    exc_info=True)

    # async def listen_verifier(self):
    #     """ Keep the session. Sends data from connectors"""
    #     async with ClientSession(
    #             headers=self.__auth_headers) as self.session:
    #         while not self.session.closed:
    #             try:
    #                 device_id, device_str = self.__verifier_queue.get()
    #                 self.__logger.debug('Received data from BACnetVerifier: '
    #                                     f'Device[{device_id}]')
    #
    #                 # fire and forget
    #                 asyncio.create_task(
    #                     self.rq_post_device(session=self.session,
    #                                         device_id=device_id,
    #                                         data=device_str))
    #             except ClientConnectorError as e:
    #                 self.__logger.warning(
    #                     f'Cannot send data about device [{device_id}] because '
    #                     f'connection problem: {e}')
    #                 # todo: implement second attempt?
    #             except Exception as e:
    #                 self.__logger.error(f'Receive and post device error: {e}',
    #                                     exc_info=True)

    def __repr__(self):
        return 'VisioHTTPClient'

    def stop(self) -> None:
        self.__stopped = True

    @property
    def __auth_headers(self) -> dict[str, str]:
        """ Provide auth header"""
        headers = {
            'Authorization': f'Bearer {self.__bearer_token}'
        }
        return headers

    def login(self, login: str, password: str) -> tuple[str, str, str]:
        """ Perform login"""
        while (self.__bearer_token is None and
               self.__user_id is None and
               self.__auth_user_id is None):
            try:
                bearer_token, user_id, auth_user_id = self.loop.run_until_complete(
                    self.__rq_login(login=login,
                                    password=password))
            except ClientConnectorError as e:
                self.__logger.error(f'Login error: {e} Next attempt after 30 sec ...')
                sleep(30)
            else:
                return bearer_token, user_id, auth_user_id

    async def __rq_login(self, login: str, password: str) -> tuple[str, str, str]:
        self.__logger.info('Logging in to the server ...')
        url = f'{self.get_url}/auth/rest/login'
        data = {
            'login': login,
            'password': password
        }
        async with ClientSession(loop=self.loop) as session:
            async with session.post(url=url, json=data) as response:
                self.__logger.debug(f'LOGIN POST: {url}')
                data = await self.__extract_response_data(response=response)
                try:
                    bearer_token = data['token']
                    user_id = data['user_id']
                    auth_user_id = data['auth_user_id']
                except TypeError as e:
                    self.__logger.error(f'Login Error! Please check login/password: {e}')
                else:
                    self.__logger.info('Successfully log in to the server')
                    return bearer_token, user_id, auth_user_id

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

    async def rq_post_device(self, session: ClientSession, device_id: int, data) -> None:
        """ Send the polled data about the device to the post_hosts.
        """
        post_requests = [self.__rq_post_device(session=session,
                                               url=url,
                                               device_id=device_id,
                                               data=data) for url in self.post_urls]
        await asyncio.gather(*post_requests, loop=self.loop)

    async def __rq_post_device(self, session: ClientSession,
                               url: str, device_id: int, data) -> None:
        """ Sends the polled data about the device to the host.
        Now only inform about rejected devices.
        """
        # :return: list of objects id, rejected by server side. FIXME

        self.__logger.debug(f'Sending collected data about device [{device_id}]')

        url = f'{url}/vbas/gate/light/{device_id}'

        async with session.post(url=url, data=data) as response:
            self.__logger.debug(f'POST: {url}\n'
                                f'Body: {data}')
            data = await self.__extract_response_data(response=response,
                                                      sent_data=data)
            await self.__check_rejected(device_id=device_id,
                                        data=data)
            # return data

    async def __check_rejected(self, device_id: int, data: list) -> list:
        """ Inform about rejected objects.
        # todo: Now the server does not always correctly return the list with errors.

        :param data: polled by BACnet Device
        :return: list of rejected by server side.
        """
        if not data:  # all object are accepted on server side
            self.__logger.debug(f'POST-result: Device [{device_id}] '
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

    async def __rq_device_object(self, device_id: int, object_type: ObjType,
                                 session: ClientSession) -> list[dict]:
        """ Request objects by device_id and object_type
        :param device_id:
        :param object_type:
        :param session: used session
        :return: data received from the server
        """
        self.__logger.warning(f"Requesting information about device [{device_id}], "
                            f"object_type: {object_type.name_dashed} from the server ...")

        url = f'{self.get_url}/vbas/gate/get/{device_id}/{object_type.name_dashed}'

        async with session.get(url=url) as response:
            self.__logger.debug(f'GET: {url}')
            data = await self.__extract_response_data(response=response)
            return data

    async def __rq_device_objects(
            self,
            device_id: int,
            object_types: tuple[ObjType],
            session: ClientSession) -> dict[ObjType, list[dict]]:
        """ Requests types of objects by device_id
        """
        # Create list with requests
        objects_requests = [self.__rq_device_object(device_id=device_id,
                                                    object_type=object_type,
                                                    session=session) for
                            object_type in object_types]

        # Each response, if it's not empty add in dict, where key is the type of object
        # and the value is the list with objects
        device_objects = {
            obj_type: objects for
            obj_type, objects in
            zip(object_types, await asyncio.gather(*objects_requests, loop=self.loop))
            if objects
        }
        self.__logger.debug(f'For device_id: {device_id} '
                            'received objects')  #: {device_objects}')
        return device_objects

    async def rq_devices_objects(
            self,
            devices_id: tuple[int],
            obj_types: tuple[ObjType]
    ) -> dict[int, dict[ObjType, list[dict]]]:
        """ Requests types of objects for each device_id.
        For each device creates a dictionary, where the key is object_type,
        and the value is a dict with object properties.
        """
        # async with ClientSession(headers=self.__auth_headers) as session:
        # Create list with requests
        devices_requests = [self.__rq_device_objects(device_id=device_id,
                                                     object_types=obj_types,
                                                     session=self.session) for
                            device_id in devices_id]
        devices = {
            device_id: device_objects for
            device_id, device_objects in
            zip(devices_id, await asyncio.gather(*devices_requests, loop=self.loop))
            if device_objects  # drops devices with no objects
        }
        return devices

    async def __extract_response_data(self, response: ClientResponse,
                                      sent_data=None) -> list or dict:
        """ Checks the correctness of the response.
        :param response: server's response
        :param sent_data request body
        :return: response['data'] field
        """
        if response.status == 200:
            resp_json = await response.json()
            if resp_json['success']:
                self.__logger.debug('Received information from the server.')
                return resp_json['data']
            else:
                self.__logger.warning(
                    f'\nServer returned failure response: url: {response.url}\n'
                    f'Request body: {sent_data}\n'
                    f'Response body: {resp_json}')
        else:
            self.__logger.warning(f'Server response status error: {response.status}')

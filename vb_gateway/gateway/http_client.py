import asyncio
from multiprocessing import SimpleQueue
from pathlib import Path
from threading import Thread
from time import sleep

from aiohttp import ClientResponse, ClientConnectorError, ClientSession

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

        # fixme: Now must be same
        self.__get_host: str = config['get_host']
        self.__get_auth = {
            'login': config['auth']['login'],
            'password': config['auth']['password'],
            'user_id': '',
            'bearer_token': '',
            'auth_user_id': ''
        }
        self.__post_hosts: list[str] = config['post_hosts']
        # fixme: implement different auth data
        self.__post_auth = {
            host: {
                'login': config['auth']['login'],
                'password': config['auth']['password'],
                'user_id': '',
                'bearer_token': '',
                'auth_user_id': ''
            } for host in self.__post_hosts}
        self.__port = config['port']

        # self.__login = config['auth']['login']
        # self.__password = config['auth']['password']

        # self.__session = None
        self.__connected = False

        # getting this data after login
        # self.__user_id = None
        # self.__bearer_token = None
        # self.__auth_user_id = None

        self.__logger.info(f'{self} starting ...')
        self.__stopped = False
        self.start()

    def run(self) -> None:
        """ Keeps the connection to the server. Login if necessary.
            Periodically requests updates from the server.
            Sends data from connectors.
        """
        while not self.__stopped:
            if self.__connected:  # IF AUTHORIZED
                try:
                    device_id, device_str = self.__verifier_queue.get()
                    self.__logger.debug('Received data from BACnetVerifier: '
                                        f'Device[{device_id}]')
                    # todo: refactor - use one loop
                    #   change to fire and forget
                    asyncio.run(self.rq_post_device(device_id=device_id, data=device_str))
                except Exception as e:
                    self.__logger.error(f"Receive'n'post device error: {e}", exc_info=True)

            else:  # IF NOT AUTHORIZED
                try:
                    # asyncio.run(self.__rq_login())
                    asyncio.run(self.login(
                        get_addr=self.get_url(host=self.__get_host, port=self.__port),
                        get_auth=self.__get_auth,
                        post_addrs=[self.get_url(host=host, port=self.__port) for
                                    host in self.__post_hosts],
                        post_auth=self.__post_auth
                    ))
                except ClientConnectorError as e:
                    self.__logger.error(f'Login error: {e}'
                                        'Sleeping 30 sec ...')  # , exc_info=True)
                    sleep(30)
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

    # @property
    # def __address(self) -> str:
    #     return f'http://{self.__get_host}:{str(self.__port)}'
    #     # return ':'.join((self.__get_host, str(self.__port)))

    # @property
    # def get_url(self) -> str:
    #     return 'http://' + ':'.join((self.__get_host, str(self.__port)))

    # @property
    # def post_urls(self) -> list[str, ...]:
    #     return ['http://' + ':'.join((post_host, self.__port))
    #             for post_host in self.__post_hosts]

    @staticmethod
    def get_url(host: str, port: int = 8080) -> str:
        return 'http://' + ':'.join((host, str(port)))

    @staticmethod
    def get_auth_headers(auth_data: dict) -> dict[str, str]:
        headers = {
            'Authorization': f"Bearer {auth_data['bearer_token']}"
        }
        return headers

    # @property
    # def __auth_headers(self) -> dict[str, str]:
    #     headers = {
    #         'Authorization': f'Bearer {self.__bearer_token}'
    #     }
    #     return headers

    async def login(self, get_addr: str, get_auth: dict,
                    post_addrs: list[str], post_auth: dict[str, dict]) -> None:
        """ Perform async auth to several servers
        Update auth dicts."""
        async with ClientSession() as session:
            if get_addr in post_addrs:
                rq_tasks = [self.__rq_login(addr=self.get_url(host=host,
                                                              port=self.__port),
                                            login=auth[host]['login'],
                                            password=auth[host]['password'],
                                            session=session
                                            ) for host, auth in post_auth.items()]

                for post_addr, auth_resp in zip(post_addrs,
                                                await asyncio.gather(*rq_tasks)):
                    try:
                        post_auth[post_addr]['user_id'] = auth_resp[0]
                        post_auth[post_addr]['bearer_token'] = auth_resp[1]
                        post_auth[post_addr]['auth_user_id'] = auth_resp[2]
                    except LookupError as e:
                        self.__logger.warning(f'Auth error: {e}', exc_info=True)
                get_auth['user_id'] = post_auth[get_addr]['user_id']
                get_auth['bearer_token'] = post_auth[get_addr]['bearer_token']
                get_auth['auth_user_id'] = post_auth[get_addr]['auth_user_id']
            else:
                raise NotImplementedError  # todo

    async def __rq_login(self, addr: str, login: str, password: str,
                         session: ClientSession) -> tuple[str, str, str]:
        self.__logger.info('Logging in to the server ...')
        url = f'{addr}/auth/rest/login'
        data = {
            'login': login,
            'password': password
        }
        async with session.post(url=url, json=data) as response:
            self.__logger.debug(f'POST: {url}')
            data = await self.__extract_response_data(response=response)
            try:
                user_id = data['user_id']
                bearer_token = data['token']
                auth_user_id = data['auth_user_id']
                return user_id, bearer_token, auth_user_id
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

    async def rq_post_device(self, device_id: int, data):
        """ Send data to several servers async"""
        async with ClientSession() as session:
            rq_tasks = [self.__rq_post_device(host=host, device_id=device_id, data=data,
                                              session=session) for host in
                        self.__post_hosts]
            await asyncio.gather(*rq_tasks)

    async def __rq_post_device(self, host: str, device_id: int, data,
                               session: ClientSession) -> None:
        """ Sends the polled information about the device to the server.
        Now only inform about rejected devices.

        # :return: list of objects id, rejected by server side.
        """
        self.__logger.debug(f'Sending collected data about device [{device_id}]')
        url = f'{self.get_url(host=host, port=self.__port)}/vbas/gate/light/{device_id}'

        async with session.post(url=url, data=data, headers={
            self.get_auth_headers(auth_data=self.__post_auth[host])
        }) as response:
            self.__logger.debug(f'POST: {url}\n'
                                f'Body: {data}')
            data = await self.__extract_response_data(response=response)
            await self.__check_rejected(device_id=device_id,
                                        data=data)
            # return data

    async def __check_rejected(self, device_id: int, data: list) -> list:
        """
        Inform about rejected objects.

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

    async def __rq_device_object(self, device_id: int, object_type: ObjType) -> list[dict]:
        """ Request of all available objects by device_id and object_type
        :param device_id:
        :param object_type:
        :return: data received from the server
        """
        self.__logger.debug(f"Requesting information about device [{device_id}], "
                            f"object_type: {object_type.name_dashed} from the server ...")

        url = (f'{self.get_url(host=self.__get_host, port=self.__port)}/'
               f'vbas/gate/get/{device_id}/{object_type.name_dashed}')

        async with ClientSession(
                headers=self.get_auth_headers(auth_data=self.__get_auth)) as session:
            async with session.get(url=url) as response:
                self.__logger.debug(f'GET: {url}')
                data = await self.__extract_response_data(response=response)
                return data

    async def __rq_objects_for_device(
            self, device_id: int,
            object_types: tuple[ObjType]) -> dict[ObjType, list[dict]]:
        """ Requests types of objects by device_id
        """
        # Create list with requests
        objects_requests = [self.__rq_device_object(device_id=device_id,
                                                    object_type=object_type) for
                            object_type in object_types]

        # Each response, if it's not empty add in dict, where key is the type of object
        # and the value is the list with objects
        device_objects = {
            obj_type: objects for
            obj_type, objects in
            zip(object_types, await asyncio.gather(*objects_requests))
            if objects
        }
        self.__logger.debug(f'For device_id: {device_id} '
                            'received objects')  #: {device_objects}')
        return device_objects

    async def rq_devices_objects(
            self, devices_id: tuple[int],
            obj_types: tuple[ObjType]) -> dict[int, dict[ObjType, list[dict]]]:
        """ Requests types of objects for each device_id.
            For each device creates a dictionary, where the key is object_type,
            and the value is a dict with object properties.
        """
        # Create list with requests
        devices_requests = [self.__rq_objects_for_device(device_id=device_id,
                                                         object_types=obj_types) for
                            device_id in devices_id]

        devices = {
            device_id: device_objects for
            device_id, device_objects in
            zip(devices_id, await asyncio.gather(*devices_requests))
            if device_objects
        }
        # drops devices with no objects

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

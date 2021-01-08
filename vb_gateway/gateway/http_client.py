import asyncio
from multiprocessing import SimpleQueue
from pathlib import Path
from threading import Thread
from time import sleep

from aiohttp import ClientConnectorError, ClientSession, ClientResponse

from vb_gateway.connectors.bacnet import ObjType
from vb_gateway.logs import get_file_logger
from vb_gateway.utils import VisioHTTPServerConfig

_base_path = Path(__file__).resolve().parent.parent
_log_file_path = _base_path / f'logs/{__name__}.log'
_log = get_file_logger(logger_name=__name__,
                       size_bytes=50_000_000,
                       file_path=_log_file_path)


class VisioHTTPClient(Thread):
    def __init__(self, gateway, verifier_queue: SimpleQueue, config: dict):
        super().__init__()

        self.setName(name=f'{self}-Thread')
        self.setDaemon(True)

        self.__gateway = gateway
        self.__verifier_queue = verifier_queue

        self.__config = config

        self.get_server_data = self.__config['get_server_data']
        self.post_servers_data = self.__config['post_servers_data']

        # self.__session = None  # todo: KEEP one session in future
        self.__connected = False

        _log.info(f'{self} starting ...')
        self.__stopped = False
        self.start()

    def run(self) -> None:
        """ Keeps the connection to the server. Login if necessary.
            Periodically requests updates from the server.
            Sends data from connectors.
        """
        # FIXME: implement attempts to login in fail case

        while not self.__stopped:
            if self.__connected:  # IF AUTHORIZED
                try:
                    device_id, device_str = self.__verifier_queue.get()
                    _log.debug('Received data from BACnetVerifier: '
                               f'Device[{device_id}]')
                    # todo: refactor - use one loop
                    #   change to fire and forget
                    asyncio.run(
                        self.rq_post_device(post_servers_data=self.post_servers_data,
                                            device_id=device_id,
                                            data=device_str
                                            ))
                except Exception as e:
                    _log.error(f"Receive or post device error: {e}", exc_info=True)

            else:  # IF NOT AUTHORIZED
                try:
                    asyncio.run(self.login(get_server_data=self.get_server_data,
                                           post_servers_data=self.post_servers_data
                                           ))
                except ClientConnectorError as e:
                    _log.warning(
                        f'Login error: {e} Sleeping 30 sec ...')  # , exc_info=True)
                    sleep(30)
                else:
                    self.__connected = True
                    _log.info('Successfully log in to the servers.')
        else:
            _log.info(f'{self} stopped.')

    def __repr__(self):
        return 'VisioClient'

    def is_connected(self) -> bool:
        return self.__connected

    def stop(self) -> None:
        self.__stopped = True
        _log.info(f'{self} was stopped.')

    async def login(self, get_server_data: VisioHTTPServerConfig,
                    post_servers_data: list[VisioHTTPServerConfig]) -> None:
        """ Perform async auth to several servers. Set auth data. """
        _log.debug(f'GET server: {get_server_data} POST servers: {post_servers_data}')
        get_in_posts = get_server_data in post_servers_data

        if get_in_posts:
            # If we send data to the server from which we receive data,
            # then we do not need to log in to this server a second time.
            post_servers_data.remove(get_server_data)

        async with ClientSession() as session:  # todo: session as param in future
            get_coro = self.__rq_login(server_data=get_server_data,
                                       session=session)
            post_cors = [self.__rq_login(server_data=post_server_data,
                                         session=session
                                         ) for post_server_data in post_servers_data]

            await asyncio.gather(get_coro, *post_cors)

        if get_in_posts:
            # Add data about the server from which we receive data
            # to the list for sending data
            post_servers_data.append(get_server_data)

    async def __rq_login(self, server_data: VisioHTTPServerConfig,
                         session: ClientSession) -> None:
        _log.info(f'Logging in to {server_data} ...')
        auth_url = server_data.base_url + '/auth/rest/login'
        async with session.post(url=auth_url, json=server_data.auth_payload) as response:
            _log.debug(f'POST: {auth_url}')
            data = await self.__extract_response_data(response=response)
            try:
                server_data.set_auth_data(bearer_token=data['token'],
                                          user_id=data['user_id'],
                                          auth_user_id=data['auth_user_id']
                                          )
                _log.info(f'Successfully authorized on {server_data}')
            except Exception as e:
                _log.error(f'Login Error! Please check {server_data}: {e}',
                           exc_info=True)
                raise e

    async def rq_post_device(self, post_servers_data: list[VisioHTTPServerConfig],
                             device_id: int, data) -> None:
        """ Send data to several servers asynchronously """
        async with ClientSession() as session:  # todo: session as param in future
            rq_tasks = [self.__rq_post_device(post_server_data=server_data,
                                              device_id=device_id,
                                              data=data,
                                              session=session
                                              ) for
                        server_data in post_servers_data]
            await asyncio.gather(*rq_tasks)

    async def __rq_post_device(self, post_server_data: VisioHTTPServerConfig,
                               device_id: int, data, session: ClientSession) -> None:
        """ Sends the polled information about the device to the server.

        # :return: list of objects id, rejected by server side.
        """
        # _log.debug(f'Sending collected data about [{device_id}] '
        #            f'device to {post_server_data} ...')
        post_url = f'{post_server_data.base_url}/vbas/gate/light/{device_id}'

        async with session.post(url=post_url,
                                data=data,
                                headers=post_server_data.auth_headers
                                ) as response:
            _log.debug(f'POST: {post_url}\n'
                       f'Body: {data}')
            _ = await self.__extract_response_data(response=response)
            # await self.__check_rejected(device_id=device_id,
            #                             data=data)
            # return data

    async def __rq_device_object(self, get_server_data: VisioHTTPServerConfig,
                                 device_id: int, object_type: ObjType,
                                 session: ClientSession) -> list[dict]:
        """ Request of all available objects by device_id and object_type
        :param device_id:
        :param object_type:
        :return: data received from the server
        """
        # _log.debug(f"Requesting information about device [{device_id}], "
        #            f"object_type: {object_type.name_dashed} from the {get_server_data} ...")

        get_url = (f'{get_server_data.base_url}'
                   f'/vbas/gate/get/{device_id}/{object_type.name_dashed}')

        # async with ClientSession(headers=get_server_data.auth_headers) as session:
        async with session.get(url=get_url) as response:
            _log.debug(f'GET: {get_url}')
            data = await self.__extract_response_data(response=response)
            return data

    async def __rq_objects_for_device(self, get_server_data: VisioHTTPServerConfig,
                                      device_id: int, object_types: tuple[ObjType],
                                      session: ClientSession) -> dict[ObjType, list[dict]]:
        """ Requests types of objects by device_id """
        # Create list with requests
        objects_requests = [self.__rq_device_object(get_server_data=get_server_data,
                                                    device_id=device_id,
                                                    object_type=object_type,
                                                    session=session
                                                    ) for
                            object_type in object_types]

        # Each response, if it's not empty add in dict, where key is the type of object
        # and the value is the list with objects
        device_objects = {obj_type: objects for
                          obj_type, objects in
                          zip(object_types, await asyncio.gather(*objects_requests))
                          if objects
                          }
        # _log.debug(f'For device_id: {device_id} received objects')  #: {device_objects}')
        return device_objects

    async def rq_devices_objects(self, get_server_data: VisioHTTPServerConfig,
                                 devices_id: tuple[int],
                                 obj_types: tuple[ObjType]
                                 ) -> dict[int, dict[ObjType, list[dict]]]:
        """ Requests types of objects for each device_id.
            For each device creates a dictionary, where the key is object_type,
            and the value is a dict with object properties.
        """
        async with ClientSession(headers=get_server_data.auth_headers) as session:
            # Create list with requests
            devices_requests = [
                self.__rq_objects_for_device(get_server_data=get_server_data,
                                             device_id=device_id,
                                             object_types=obj_types,
                                             session=session
                                             ) for
                device_id in devices_id]

            devices = {
                device_id: device_objects for
                device_id, device_objects in
                zip(devices_id, await asyncio.gather(*devices_requests))
                if device_objects
            }
            # drops devices with no objects
            return devices

    @staticmethod
    async def __extract_response_data(response: ClientResponse) -> list or dict:
        """ Checks the correctness of the response.
        :param response: server's response
        :return: response['data'] field
        """
        if response.status == 200:
            resp_json = await response.json()
            if resp_json['success']:
                _log.debug(f'Received successfully response from server: {response.url}')
                return resp_json['data']
            else:
                _log.warning(f'Server returned failure response: {response.url}\n'
                             f'{resp_json}')
        else:
            _log.warning('Server response status error: '
                         f'[{response.status}] {response.url}')

    # @staticmethod
    # async def __check_rejected(device_id: int, data: list) -> list:
    #     """ Inform about rejected objects.
    #
    #     # todo: Now the server does not always correctly return the list with errors.
    #
    #     :param data: polled by BACnet Device
    #     # :return: list of rejected by server side.
    #     """
    #     if not data:  # all object are accepted on server side
    #         _log.debug(f"POST-result: Device [{device_id}] "
    #                    "Server didn't return unaccepted objects.")
    #         return data
    #     else:
    #         rejected_objects_id = [obj[str(ObjProperty.objectIdentifier.id)] for
    #                                obj in data]
    #         _log.warning(f'POST-result: Device [{device_id}] '
    #                      'Error processing objects on '
    #                      f'the server: {rejected_objects_id}')
    #         # todo: What should we doing with rejected objects?
    #         return rejected_objects_id

import asyncio
from hashlib import md5
from multiprocessing import SimpleQueue
from os import environ
from threading import Thread
from time import sleep

import aiohttp

from gateway.connectors.bacnet import ObjType
from gateway.logs import get_file_logger

_log = get_file_logger(logger_name=__name__,
                       size_bytes=50_000_000
                       )


def periodic(period: float or int):
    def scheduler(f):
        async def wrapper(*args, **kwargs):
            while True:
                # todo: how better?
                asyncio.create_task(f(*args, **kwargs))
                await asyncio.sleep(period)  # fixme: will be deprecate

        return wrapper

    return scheduler


# TODO: example of usage:
# @periodic(2)
# async def do_something(*args, **kwargs):
#     await asyncio.sleep(5)  # Do some heavy calculation
#     print(time.time())
#
#
# if __name__ == '__main__':
#     asyncio.run(do_something('Maluzinha do papai!', secret=42))


class VisioHTTPConfig:
    """Represent parameters for Visio HTTP server."""

    # That class allows to create only one instance for each server's params
    _instances = {}  # keeps instances references

    __slots__ = ('_login', '_password_md5', 'host', 'port',
                 '_bearer_token', '_user_id', '_auth_user_id',
                 'is_connected', 'is_authorized'
                 )

    def __new__(cls, *args, **kwargs):
        # Used kwargs because __init__ accept args by key
        _args_hash = hash((kwargs.get('login'),
                           kwargs.get('password'),
                           kwargs.get('host'),
                           kwargs.get('port')
                           ))
        if cls._instances.get(_args_hash) is None:
            cls._instances[_args_hash] = super().__new__(cls)
        return cls._instances[_args_hash]

    def __init__(self, login: str, password: str, host: str, port: int):
        self.host = host
        self.port = port

        self._login = login
        self._password_md5 = md5(password.encode()).hexdigest()

        self._bearer_token = None
        self._user_id = None
        self._auth_user_id = None

        self.is_connected = True
        self.is_authorized = False

    def set_auth_data(self, bearer_token: str, user_id: int, auth_user_id: int) -> None:
        # TODO validate data
        self._bearer_token = bearer_token
        self._user_id = user_id
        self._auth_user_id = auth_user_id

        self.is_authorized = True

    @property
    def base_url(self) -> str:
        return 'http://' + ':'.join((self.host, str(self.port)))

    @property
    def auth_payload(self) -> dict[str, str]:
        data = {'login': self._login,
                'password': self._password_md5
                }
        return data

    @property
    def auth_headers(self) -> dict[str, str]:
        if isinstance(self._bearer_token, str):
            headers = {'Authorization': f'Bearer {self._bearer_token}'
                       }
            return headers

    def __repr__(self) -> str:
        _auth = 'Authorized' if self.is_authorized else 'Unauthorized'
        return f'<VisioHTTPConfig: {_auth}:{self.host} [{self._login}]>'

    @classmethod
    def read_from_env(cls, var_root: str):
        """ Creates a VisioHTTPServerConfig instance based on environment variables """
        try:
            return cls(login=environ[f'HTTP_{var_root}_LOGIN'],
                       password=environ[f'HTTP_{var_root}_PASSWORD'],
                       host=environ[f'HTTP_{var_root}_HOST'],
                       port=int(environ[f'HTTP_{var_root}_PORT']),
                       )
        except KeyError:
            _log.warning(f'{cls.__name__} cannot be read form environment variables.')
            raise EnvironmentError(
                "Please set the server parameters in environment variables:\n"
                f"'HTTP_{var_root}_HOST'\n"
                f"'HTTP_{var_root}_PORT'\n"
                f"'HTTP_{var_root}_LOGIN'\n"
                f"'HTTP_{var_root}_PASSWORD'"
            )


class VisioHTTPNode:
    """Represent Visio HTTP node (primary server + mirror server)."""

    def __init__(self, main: VisioHTTPConfig, mirror: VisioHTTPConfig):
        self.primary = main
        self.mirror = mirror

        self.cur_server = main

    @property
    def is_authorized(self) -> bool:
        return self.cur_server.is_authorized

    def __repr__(self) -> str:
        _is_authorized = f'Authorized' if self.is_authorized else 'Unauthorized'
        return f'<VisioHTTPNode: {_is_authorized}: {self.cur_server}>'

    def switch_to_mirror(self) -> None:
        """ Switches communication to mirror if the primary server is unavailable """
        self.cur_server = self.mirror

    @classmethod
    def read_from_env(cls, main_var_root: str):
        """ Creates VisioHTTPNode, contains main and mirror server from env
        :param main_var_root: name of environment variable for main server
        """
        mirror_var_root = main_var_root + '_MIRROR'
        try:
            return cls(main=VisioHTTPConfig.read_from_env(var_root=main_var_root),
                       mirror=VisioHTTPConfig.read_from_env(var_root=mirror_var_root)
                       )
        except EnvironmentError as e:
            _log.warning(f'{cls.__name__} cannot be read form environment variables.')
            raise e


class VisioHTTPClient(Thread):
    """Control interactions via HTTP."""

    upd_period = 60 * 60

    def __init__(self, gateway, verifier_queue: SimpleQueue, config: dict):
        super().__init__()

        self.setName(name=f'{self}-Thread')
        self.setDaemon(True)

        self._gateway = gateway
        self._verifier_queue = verifier_queue

        self._config = config

        self.get_server_data = self._config['get_node']
        self.post_servers_data = self._config['post_nodes']

        # self.__session = None  # todo: KEEP one session in future
        self._is_authorized = False
        self._stopped = False

    def run(self) -> None:
        """ Keeps the connection to the server.
        todo: Periodically update authorization (1h)
        todo: Periodically requests updates from the server. (1h)
        Sends data from connectors.
        """
        _log.info(f'{self} starting ...')

        while not self._stopped:
            if self._is_authorized:
                try:
                    device_id, device_str = self._verifier_queue.get()
                    _log.debug('Received data from BACnetVerifier: '
                               f'Device[{device_id}]'
                               )
                    # todo: refactor - use one loop
                    #   change to fire and forget
                    asyncio.run(
                        self.rq_post_device(post_servers_data=self.post_servers_data,
                                            device_id=device_id,
                                            data=device_str
                                            ))
                except Exception as e:
                    _log.error(f"Receive or post device error: {e}",
                               exc_info=True
                               )

            else:  # not authorized
                try:
                    self._is_authorized = asyncio.run(
                        self.login(get_node=self.get_server_data,
                                   post_nodes=self.post_servers_data
                                   ))
                except Exception as e:
                    _log.error(f'Authorization error: {e}',
                               exc_info=True
                               )
        else:
            _log.info(f'{self} stopped.')

    @periodic(period=upd_period)
    async def run_iteration(self) -> None:
        """"""
        # TODO: stop devices
        # TODO: send all collected data
        # TODO: logout
        # TODO: login
        # TODO: rq devices
        # TODO: upd devices in connectors
        # TODO: get from queue then send via HTTP

    def __repr__(self):
        return 'VisioClient'

    def is_connected(self) -> bool:
        return self._is_authorized

    def stop(self) -> None:
        self._stopped = True
        _log.info(f'{self} was stopped.')

    async def login(self, get_node: VisioHTTPNode,
                    post_nodes: list[VisioHTTPNode]) -> bool:
        """ Perform authorization to all nodes
        :param get_node:
        :param post_nodes:
        :return: can continue with current authorizations
        """
        _log.debug(f'GET node: {get_node} POST nodes: {post_nodes}')

        # todo: session as param in future (for reuse one session)
        async with aiohttp.ClientSession() as session:
            get_coro = self._login_node(node=get_node,
                                        session=session
                                        )
            post_coros = [self._login_node(node=node,
                                           session=session
                                           ) for node in post_nodes]
            res = await asyncio.gather(get_coro, *post_coros)

            is_get_authorized = res[0]
            is_post_authorized = any(res[1:])
            successfully_authorized = bool(is_get_authorized and is_post_authorized)

            if successfully_authorized:
                _log.info(f'Successfully authorized to {get_node}, {post_nodes}')
            else:
                _log.warning(f'Authorizations failed!'
                             f'Next attempt after {self._config["delay_attempt"]}'
                             )
                sleep(self._config["delay_attempt"])

            return successfully_authorized

    async def _login_node(self, node: VisioHTTPNode,
                          session) -> bool:
        """ Perform authorization to node (primary server + mirror)
        :param node: node on witch the authorization is performed
        :param session:
        :return: is node authorized
        """
        _log.info(f'Authorization to {node} ...')
        try:
            is_authorized = await self._login_server(server=node.cur_server,
                                                     session=session
                                                     )
            if not is_authorized:
                node.switch_to_mirror()
                is_authorized = await self._login_server(server=node.cur_server,
                                                         session=session
                                                         )
            if is_authorized:
                _log.info(f'Successfully authorized on {node}')
            else:
                _log.warning(f'Authorization on {node} failed!')
        except Exception as e:
            _log.warning(f'Authorization error! Please check {node}: {e}',
                         exc_info=True
                         )
        finally:
            return node.is_authorized

    async def _login_server(self, server: VisioHTTPConfig,
                            session) -> bool:
        """ Perform authorization to server
        :param server: server on which the authorization is performed
        :param session:
        :return: is server authorized
        """
        if server.is_authorized:
            return True

        _log.info(f'Authorization to {server} ...')
        auth_url = server.base_url + '/auth/rest/login'
        try:
            auth_data = await self._rq(method='POST',
                                       url=auth_url,
                                       json=server.auth_payload,
                                       session=session
                                       )
            server.set_auth_data(bearer_token=auth_data['token'],
                                 user_id=auth_data['user_id'],
                                 auth_user_id=auth_data['auth_user_id']
                                 )
            if server.is_authorized:
                _log.info(f'Successfully authorized on {server}')
            else:
                _log.info(f'Authorization on {server} failed!')

        except aiohttp.ClientError as e:
            _log.warning(f'Authorization on {server} was failed: {e}')
            # raise e
        except Exception as e:
            _log.error(f'Authorization error! Please check {server}: {e}',
                       exc_info=True
                       )
            # raise e
        finally:
            return server.is_authorized

    # async def _rq_login(self, url: str, auth_payload: dict,
    #                     session) -> list or dict:
    #     async with session.post(url=url, json=auth_payload) as resp:
    #         _log.debug(f'POST: {resp.url}')
    #         # try:
    #         return await self._extract_response_data(response=resp)
    #         # except ClientError as e:
    #         #     raise e

    async def rq_post_device(self, post_servers_data: list[VisioHTTPConfig],
                             device_id: int, data) -> None:
        """ Send data to several servers asynchronously """
        # todo return bool
        try:
            # todo: session as param in future
            async with aiohttp.ClientSession() as session:
                rq_tasks = [self.__rq_post_device(post_server_data=server_data,
                                                  device_id=device_id,
                                                  data=data,
                                                  session=session
                                                  ) for
                            server_data in post_servers_data]
                await asyncio.gather(*rq_tasks)
        except aiohttp.ClientError as e:
            _log.warning(f'Error: {e}')

    async def __rq_post_device(self, post_server_data: VisioHTTPConfig,
                               device_id: int, data,
                               session) -> None:
        """ Sends the polled information about the device to the server.

        # :return: list of objects id, rejected by server side.
        """

        post_url = f'{post_server_data.base_url}/vbas/gate/light/{device_id}'

        async with session.post(url=post_url,
                                data=data,
                                headers=post_server_data.auth_headers
                                ) as response:
            _log.debug(f'POST: {post_url}\n'
                       f'Body: {data}')
            _ = await self._extract_response_data(response=response)
            # await self.__check_rejected(device_id=device_id,
            #                             data=data)
            # return data

    # async def get_devices(self, get_node: VisioHTTPNode,
    #                       devices_id: tuple[int], obj_types: tuple[ObjType]
    #                       ) -> dict[int, dict[ObjType, list[dict]]]:
    #     """ Requests objects of each type for each device_id.
    #     For each device creates a dictionary, where the key is object_type,
    #     and the value is a dict with object properties.
    #     """
    #     # todo: session as param
    #
    #     # TODO: do we need this method?
    #     async with aiohttp.ClientSession(
    #             headers=get_node.cur_server.auth_headers) as session:
    #         devices_coros = [self.__rq_objects_for_device(get_server_data=get_node,
    #                                                       device_id=device_id,
    #                                                       object_types=obj_types,
    #                                                       session=session
    #                                                       ) for device_id in devices_id]
    #         devices = {device_id: device_objects for
    #                    device_id, device_objects in
    #                    zip(devices_id, await asyncio.gather(*devices_coros))
    #                    if device_objects
    #                    }
    #         # drops devices with no objects
    #         return devices

    async def get_device(self, node: VisioHTTPNode,
                         device_id: int, obj_types: tuple[ObjType],
                         session) -> dict[ObjType, list[dict]]:
        """Perform request objects of each types for device by id."""
        obj_coros = [
            self._rq(method='GET',
                     url=(f'{node.cur_server.base_url}'
                          f'/vbas/gate/get/{device_id}/{obj_type.name_dashed}'),
                     session=session,
                     headers=node.cur_server.auth_headers
                     ) for obj_type in obj_types
        ]
        # objects of each type, if it's not empty, are added to the dictionary,
        # where key is obj_type and value is list with objects
        device_objects = {obj_type: objs for
                          obj_type, objs in
                          zip(obj_types, await asyncio.gather(*obj_coros))
                          if objs
                          }
        # _log.debug(f'For device_id: {device_id} received objects')  #: {device_objects}')
        return device_objects

    # async def _rq_get_obj_type(self, get_node: VisioHTTPNode,
    #                            device_id: int, object_type: ObjType,
    #                            session) -> list[dict]:
    #     """ Request of all available objects by device_id and object_type
    #     :param device_id:
    #     :param object_type:
    #     :return: data received from the server
    #     """
    #     # _log.debug(f"Requesting information about device [{device_id}], "
    #     #            f"object_type: {object_type.name_dashed} from the {get_server_data} ...")
    #
    #     get_url = (f'{get_node.cur_server.base_url}'
    #                f'/vbas/gate/get/{device_id}/{object_type.name_dashed}'
    #                )
    #     try:
    #         # async with ClientSession(headers=get_server_data.auth_headers) as session:
    #         async with session.get(url=get_url) as response:
    #             _log.debug(f'GET: {get_url}')
    #             data = await self._extract_response_data(response=response)
    #             return data
    #     except aiohttp.ClientError as e:
    #         _log.warning(f'Error: {e}')

    async def _rq(self, method: str, url: str, session, **kwargs) -> list or dict:
        """Perform HTTP request and check response
        :return: extracted data
        """
        # todo: need re-raise?
        _log.debug(f'{method}: {url}')
        async with session.request(method=method, url=url, **kwargs) as resp:
            data = await self._extract_response_data(response=resp)
            return data

    @staticmethod
    async def _extract_response_data(response) -> list or dict:
        """ Checks the correctness of the response.
        :param response: server's response
        :return: response['data'] field after checks
        """
        if response.status == 200:
            resp_json = await response.json()
            if resp_json['success']:
                _log.debug(f'Received successfully response from server: {response.url}')
                return resp_json['data']
            else:
                # todo: switch to another server
                # _log.warning(f'Server returned failure response: {response.url}\n'
                #              f'{resp_json}')
                raise aiohttp.ClientError(
                    f'Server returned failure response: {response.url}\n'
                    f'{resp_json}'
                )
        else:
            # todo: switch to another server
            # _log.warning('Server response status error: '
            #              f'[{response.status}] {response.url}')
            raise aiohttp.ClientError('Server response status error: '
                                      f'[{response.status}] {response.url}'
                                      )

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

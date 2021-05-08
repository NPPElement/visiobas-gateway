import asyncio
from pathlib import Path
from typing import Iterable, Any, Union, Collection

import aiohttp
from yarl import URL

from models import HTTPServerConfig
from .http_node import VisioHTTPNode
from ...models import ObjType
from ...utils import get_file_logger

_LOG = get_file_logger(name=__name__)
# _base_path = Path(__file__).resolve().parent.parent.parent

# aliases
VisioBASGateway = Any  # '...gateway_loop.VisioBASGateway'


class VisioBASHTTPClient:
    """Control interactions via HTTP."""

    _AUTH_URL = 'auth/rest/login'
    _LOGOUT_URL = 'auth/secure/logout'
    _GET_URL = 'vbas/gate/get'
    _POST_URL = 'vbas/gate/light'

    def __init__(self, gateway: 'VisioBASGateway', config: dict):
        self.gateway = gateway
        self._config = config
        self._timeout = aiohttp.ClientTimeout(total=self._config.get('timeout', 30))
        self._session = aiohttp.ClientSession(timeout=self.timeout)

        self._get_node = VisioHTTPNode.from_dict(config=self._config['get_node'])
        self._post_nodes = [VisioHTTPNode.from_dict(config=list(node.values()).pop())
                            for node in self._config['post']]

        self._upd_task = None
        self._authorized = False
        # self._stopped = False

    def __repr__(self) -> str:
        return self.__class__.__name__

    @classmethod
    def from_yaml(cls, gateway: 'VisioBASGateway',
                  yaml_path: Path) -> 'VisioBASHTTPClient':
        """Create HTTP client with configuration read from YAML file."""
        import yaml

        with yaml_path.open() as cfg_file:
            config = yaml.load(cfg_file, Loader=yaml.FullLoader)
            _LOG.info(f'Creating {cls.__name__} from {yaml_path}')
        return cls(gateway=gateway, config=config)

    @property
    def timeout(self) -> aiohttp.ClientTimeout:
        return self._timeout

    @property
    def authorized(self) -> bool:
        return self._authorized

    @property
    def retry_delay(self) -> int:
        return self._config['delay'].get('retry', 60)

    @property
    def upd_delay(self) -> int:
        return self._config['delay'].get('update', 60 * 60)

    @property
    def get_node(self) -> VisioHTTPNode:
        return self._get_node

    @property
    def post_nodes(self) -> Collection[VisioHTTPNode]:
        return self._post_nodes

    @property
    def all_nodes(self) -> list[VisioHTTPNode]:
        return [self._get_node, *self._post_nodes]

    async def setup(self) -> None:
        """Wait for authorization then spawn a periodic update task."""
        await self.authorize(retry=self.retry_delay)

        # self._upd_task = self.gateway.loop.create_task(self.periodic_update())

    # async def periodic_update(self) -> None:
    #     """Perform periodically reauthorize."""
    #     # await asyncio.sleep(delay=self.upd_delay)
    #     # todo kill/wait pending tasks
    #     await self.logout(nodes=self.all_nodes)
    #     await self.authorize(retry=self.retry_delay)
    #     # self._upd_task = self.gateway.loop.create_task(self.periodic_update())

    # async def run_http_post_loop(self, queue: asyncio.Queue,
    #                              post_nodes: Iterable[VisioHTTPNode],
    #                              session
    #                              ) -> None:
    #     """Listen queue from verifier.
    #     When receive data from verifier - send it to nodes via HTTP.
    #
    #     Designed as an endless loop. Can be stopped from gateway thread.
    #     """
    #     _log.info('Sending via HTTP loop started')
    #     # Loop that receive data from verifier then send it to nodes via HTTP.
    #     while not self._stopped:
    #         try:
    #             device_id, device_str = await queue.get()
    #             _log.debug('Received data from BACnetVerifier: '
    #                        f'Device[{device_id}]'
    #                        )
    #             # todo: change to fire and forget?
    #             _ = await self.post_device(nodes=post_nodes,
    #                                        device_id=device_id,
    #                                        data=device_str,
    #                                        session=session
    #                                        )
    #         except Exception as e:
    #             _log.error(f"Receive or post error: {e}",
    #                        exc_info=True
    #                        )
    #     else:  # received stop signal
    #         _log.info(f'{self} stopped.')

    # async def run_ws_send_loop(self, queue: SimpleQueue,
    #                            post_nodes: Iterable[VisioHTTPNode],
    #                            session) -> None:
    #     """Listen queue from verifier.
    #     When receive data from verifier - send it to nodes via websocket.
    #
    #     Designed as an endless loop. Can be stopped from gateway thread.
    #     """
    #     _log.info('Sending via websocket loop started')
    #     # Loop that receive data from verifier then send it to nodes via websocket.
    #     while not self._stopped:
    #         try:
    #             raise NotImplementedError  # todo
    #
    #         except Exception as e:
    #             _log.error(f'Receive or send device error: {e}',
    #                        exc_info=True
    #                        )
    #     else:  # received stop signal
    #         _log.info(f'{self} stopped.')

    # def stop(self) -> None:
    #     self._stopped = True
    #     _log.info(f'Stopping {self} ...')
    #     asyncio.run(
    #         self.logout(nodes=[self.get_node, *self.post_nodes])
    #     )

    async def get_objs(self, dev_id: int, obj_types: Collection[ObjType]
                       ) -> Union[tuple[Any], Any]:
        """
        Returns:
            If provided one type - returns objects of this type.
            If provided several types - returns tuple of objects.
        """
        rq_tasks = [self._rq(method='GET',
                             url=self.get_node.cur_server.url / self._GET_URL / str(
                                 dev_id) / obj_type.name_dashed,
                             headers=self.get_node.cur_server.auth_headers)
                    for obj_type in obj_types]
        data = await asyncio.gather(*rq_tasks)

        return data[0] if len(obj_types) == 1 else data

    async def logout(self, nodes: Iterable[VisioHTTPNode]) -> bool:
        """Perform log out from nodes.
        :param nodes:
        :return: is logout successful
        """
        _LOG.debug(f'Logging out from: {nodes} ...')
        try:
            logout_tasks = [self._rq(method='GET',
                                     url=node.cur_server.url / self._LOGOUT_URL,
                                     headers=node.cur_server.auth_headers
                                     ) for node in nodes]
            res = await asyncio.gather(*logout_tasks)

            # forget auth data
            [node.cur_server.clear_auth_data() for node in nodes]

            _LOG.info(f'Logout from {nodes}: {res}')
            return True

        except aiohttp.ClientResponseError as e:
            _LOG.warning(f'Failure logout: {e}')
            return False
        except Exception as e:
            _LOG.error(f'Logout error: {e}',
                       exc_info=True
                       )
            return False

    # todo use async_backoff decorator for retry?
    async def authorize(self, retry: int = 60) -> None:
        """Ensures the authorization.

        Args:
            retry: time to sleep after failed authorization before next attempt
        """
        while not self._authorized:
            self._authorized = await self.login(get_node=self._get_node,
                                                post_nodes=self._post_nodes,
                                                )
            if not self._authorized:
                await asyncio.sleep(delay=retry)

    async def login(self, get_node: VisioHTTPNode,
                    post_nodes: Iterable[VisioHTTPNode]) -> bool:
        """Perform authorization to all nodes.
        :param get_node:
        :param post_nodes:
        :return: can continue with current authorizations

        # fixme: use `extra`
        """
        _LOG.debug(f'Logging in to GET:{get_node}, POST:{post_nodes}...')

        res = await asyncio.gather(
            self._login_node(node=get_node),
            *[self._login_node(node=node) for node in post_nodes]
        )
        is_get_authorized = res[0]  # always one instance of get server -> [0]
        is_post_authorized = any(res[1:])
        successfully_authorized = bool(is_get_authorized and is_post_authorized)

        if successfully_authorized:
            _LOG.info(f'Successfully authorized to GET:{get_node}, POST:{post_nodes}')
        else:
            _LOG.warning('Failed authorizations!')
        return successfully_authorized

    async def _login_node(self, node: VisioHTTPNode) -> bool:
        """Perform authorization to node (primary server or mirror)

        Args:
            node: Node to authorize

        Returns:
            Node is authorized

        # fixme: use `extra`
        """
        _LOG.debug(f'Authorization to {repr(node)}')
        try:
            is_authorized = await self._login_server(server=node.cur_server)
            if not is_authorized:
                switched = node.switch_to_mirror()
                if switched:
                    is_authorized = await self._login_server(server=node.cur_server)
            if is_authorized:
                _LOG.info(f'Successfully authorized to {repr(node)}')
            else:
                _LOG.warning(f'Failed authorization to {repr(node)}')
        except Exception as e:
            _LOG.exception(f'Authorization error! Please check {repr(node)}: {e}')
        finally:
            return node.is_authorized

    async def _login_server(self, server: HTTPServerConfig) -> bool:
        """Perform authorization to server.

        Args:
            server: Server to authorize

        Returns:
            Server is authorized

        # fixme: use `extra`
        """
        if server.is_authorized:
            return True

        _LOG.debug(f'Authorization to {server}...')
        try:
            auth_data = await self._rq(method='POST',
                                       url=server.url / self._AUTH_URL,
                                       json=server.auth_payload)
            server.set_auth_data(**auth_data)
            _LOG.debug(f'Successfully authorized to {server}')
        except aiohttp.ClientError as e:
            _LOG.warning(f'Failed authorization to {server}: {e}')
        except Exception as e:
            _LOG.exception(f'Failed authorization to  {server}: {e}',
                           extra={'url': server.url, 'exception': str(e)})
        finally:
            return server.is_authorized

    async def post_device(self, nodes: Collection[VisioHTTPNode],
                          device_id: int, data: str) -> bool:
        """Perform POST requests with data to nodes.
        :param nodes:
        :param device_id:
        :param data:
        :return: is POST requests successful
        """
        try:
            post_tasks = [
                self._rq(method='POST',
                         url=node.cur_server.url / self._POST_URL / str(device_id),
                         headers=node.cur_server.auth_headers,
                         data=data
                         ) for node in nodes
            ]
            await asyncio.gather(*post_tasks)
            _LOG.debug(f'Successfully sent [{device_id}]\'s data to {nodes}')
            return True
        except Exception as e:
            _LOG.exception(f'Failed to send: {e}')
            return False

    async def _rq(self, method: str, url: Union[str, URL], **kwargs) -> Union[list, dict]:
        """Perform HTTP request and check response.
        :return: extracted data
        """
        # todo: need re-raise?
        _LOG.debug(f'{method}: {url}')
        async with self._session.request(method=method, url=url, **kwargs) as resp:
            data = await self._extract_response_data(response=resp)
            return data

    @staticmethod
    async def _extract_response_data(response: aiohttp.ClientResponse) -> list or dict:
        """ Checks the correctness of the response.
        :param response: server's response
        :return: response['data'] field after checks
        """
        response.raise_for_status()

        if response.status == 200:
            response.raise_for_status()
            _json = await response.json()
            if _json['success']:
                _LOG.debug(f'Successfully response: {response.url}')
                try:
                    return _json['data']
                except LookupError as e:
                    # fixme
                    _LOG.warning(f'Extracting failed (most likely in logout): {e}',
                                 # exc_info=True
                                 )
            else:
                raise aiohttp.ClientError(
                    f'Failure response: {response.url}\n{_json}'
                )
        # else:
        #     # todo: switch to another server
        #     # _log.warning('Server response status error: '
        #     #              f'[{response.status}] {response.url}')
        #     raise aiohttp.ClientError('Response status: '
        #                               f'[{response.status}] {response.url}'
        #                               )

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

    # async def run_modbus_simulation_loop(self):
    #     """Loop for modbus simulation."""
    #     # fixme Isn't loop.
    #     _log.critical(f'Starting {self} in modbus simulation mode.')
    #     try:
    #         from gateway.connector.modbus import ModbusConnector
    #         # Does not start normally. Therefore parameters can be skipped.
    #
    #         # The queue is not for the verifier!
    #         # Used to transfer data from http to modbus server.
    #         # No queue for verifier.
    #         modbus_connector = ModbusConnector(gateway='',
    #                                            getting_queue=self._getting_queue,
    #                                            verifier_queue=None,
    #                                            config={}
    #                                            )
    #         async with aiohttp.ClientSession(timeout=self._timeout) as session:
    #             while not self._is_authorized:
    #                 self._is_authorized = await self.login(get_node=self.get_node,
    #                                                        post_nodes=self.post_nodes,
    #                                                        session=session
    #                                                        )
    #
    #             # The queue from the connector is read by the modbus simulation server.
    #             is_updated = await self.upd_connector(node=self.get_node,
    #                                                   connector=modbus_connector,
    #                                                   session=session
    #                                                   )
    #             _log.critical(f'Modbus device sent to modbus server: {is_updated}')
    #
    #             # fixme: expected only one device in address_cache
    #             device_address = list(modbus_connector.address_cache.values()).pop()
    #             self._getting_queue.put(device_address)
    #
    #             self._stopped = True
    #             _log.info(f'Stopping {self} ...')
    #             await self.logout(nodes=[self.get_node, *self.post_nodes])
    #
    #     except Exception as e:
    #         _log.warning(f'Test modbus loop error: {e}',
    #                      exc_info=True
    #                      )

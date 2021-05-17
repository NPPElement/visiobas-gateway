import asyncio
from typing import Any, Union, Collection, Optional

import aiohttp

from ...models import (ObjType, HTTPServerConfig, HTTPSettings)
from ...utils import get_file_logger

_LOG = get_file_logger(name=__name__)
# _base_path = Path(__file__).resolve().parent.parent.parent

# aliases
VisioBASGateway = Any  # '...gateway_loop.VisioBASGateway'


class VisioHTTPClient:
    """Control interactions via HTTP."""

    _AUTH_URL = 'auth/rest/login'
    _LOGOUT_URL = '/auth/secure/logout'
    _GET_URL = '/vbas/gate/get/'
    _POST_URL = 'vbas/gate/light'

    def __init__(self, gateway: 'VisioBASGateway', settings: HTTPSettings):
        self.gateway = gateway
        self._config = settings
        self._timeout = aiohttp.ClientTimeout(total=settings.timeout)
        self._session = aiohttp.ClientSession(timeout=settings.timeout)

        # self._upd_task = None
        self._authorized = False
        # self._stopped = False

    def __repr__(self) -> str:
        return self.__class__.__name__

    @property
    def timeout(self) -> aiohttp.ClientTimeout:
        return self._timeout

    @property
    def authorized(self) -> bool:
        return self._authorized

    @property
    def retry_delay(self) -> int:
        return self._config.retry

    @property
    def server_get(self) -> HTTPServerConfig:
        return self._config.server_get

    @property
    def servers_post(self) -> list[HTTPServerConfig]:
        return self._config.servers_post

    async def setup(self) -> None:
        """Wait for authorization then spawn a periodic update task."""
        await self.wait_login(retry=self.retry_delay)

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
        """Requests objects of provided type

        Args:
            dev_id: device identifier
            obj_types: types of objects

        Returns:
            If provided one type - returns objects of this type.
            If provided several types - returns tuple of objects.
        """
        rq_tasks = [self._rq(method='GET',
                             url=self.server_get.current_url + self._GET_URL + str(
                                 dev_id) + '/' + obj_type.name_dashed,
                             headers=self.server_get.auth_headers)
                    for obj_type in obj_types]
        data = await asyncio.gather(*rq_tasks)

        return data[0] if len(obj_types) == 1 else data

    async def logout(self, servers: Optional[Collection[HTTPServerConfig]] = None) -> bool:
        """Performs log out from servers.

        Args:
            servers: Servers to perform logout.
                    If None - perform logout from all servers.

        Returns:
            True: Successful logout
            False: Failed logout
        """
        servers = servers or [self.server_get, *self.servers_post]

        _LOG.debug(f'Logging out from: {servers} ...')
        try:
            logout_tasks = [self._rq(method='GET',
                                     url=server.current_url + self._LOGOUT_URL,
                                     headers=server.auth_headers
                                     ) for server in servers]
            res = await asyncio.gather(*logout_tasks)

            # clear auth data
            [server.clear_auth_data() for server in servers]

            _LOG.info(f'Logout from {servers}: {res}')
            return True

        except aiohttp.ClientResponseError as e:
            _LOG.warning(f'Failure logout: {e}')
            return False
        except Exception as e:
            _LOG.exception(f'Logout error: {e}')
            return False

    # todo use async_backoff decorator for retry?
    async def wait_login(self, retry: int = 60) -> None:
        """Ensures the authorization.

        Args:
            retry: Time to sleep after failed authorization before next attempt
        """
        while not self._authorized:
            self._authorized = await self.login(get_server=self.server_get,
                                                post_servers=self.servers_post,
                                                )
            if not self._authorized:
                await asyncio.sleep(delay=retry)

    async def login(self, get_server: HTTPServerConfig,
                    post_servers: Collection[HTTPServerConfig]) -> bool:
        """Perform authorization to all servers, required for work.

        Args:
            get_server: Server to send GET requests
            post_servers: Servers to send POST requests

        Returns:
            True: Can continue with current authorizations
            False: Cannot continue

        # fixme: use `extra`
        """
        _LOG.debug(f'Logging in to GET:{get_server}, POST:{post_servers}...')

        res = await asyncio.gather(
            self._login_server(server=get_server),
            *[self._login_server(server=server) for server in post_servers]
        )
        is_get_authorized = res[0]  # always one instance of get server -> [0]
        is_post_authorized = any(res[1:])
        successfully_authorized = bool(is_get_authorized and is_post_authorized)

        if successfully_authorized:
            _LOG.info(f'Successfully authorized to GET:{get_server}, POST:{post_servers}')
        else:
            _LOG.warning('Failed authorizations!')
        return successfully_authorized

    async def _login_server(self, server: HTTPServerConfig) -> bool:
        """Perform authorization to server (primary server or mirror)

        Args:
            server: Server to authorize

        Returns:
            True: Server is authorized
            False: Server is not authorized

        # fixme: use `extra`
        """
        _LOG.debug(f'Authorization to {server}')
        try:
            # auth_data = await self._rq(method='POST',
            #                            url=server.current_url + '/' + self._AUTH_URL,
            #                            json=server.auth_payload)
            # server.set_auth_data(**auth_data)
            while not server.is_authorized:  # and server.switch_server():
                auth_data = await self._rq(method='POST',
                                           url=server.current_url + '/' + self._AUTH_URL,
                                           json=server.auth_payload)
                server.set_auth_data(**auth_data)

                if not server.switch_current():
                    break

            if server.is_authorized:
                _LOG.info(f'Successfully authorized to {server}')
            else:
                _LOG.warning(f'Failed authorization to {server}')
        except aiohttp.ClientError as e:
            _LOG.warning(f'Failed authorization to {server}: {e}')
        except Exception as e:
            _LOG.exception(f'Failed authorization to  {server}: {e}',
                           extra={'url': server.current_url, 'exception': str(e)})
        finally:
            return server.is_authorized

    async def post_device(self, servers: Collection[HTTPServerConfig],
                          dev_id: int, data: str) -> bool:
        """Performs POST requests with data to servers.

        Args:
            servers: servers to send POST requests to
            dev_id: device identifier
            data: body of POST request

        Returns:
            POST request is successful
        """
        try:
            post_tasks = [
                self._rq(method='POST',
                         url=server.current_url + '/' + self._POST_URL + '/' + str(dev_id),
                         headers=server.auth_headers,
                         data=data
                         ) for server in servers
            ]
            await asyncio.gather(*post_tasks)
            _LOG.debug(f'Successfully sent [{dev_id}]\'s data to {servers}')
            return True
        except Exception as e:
            _LOG.exception(f'Failed to send: {e}')
            return False

    async def _rq(self, method: str, url: str, **kwargs) -> Union[list, dict]:
        """Perform HTTP request and check response.
        :return: extracted data
        """
        # todo: need re-raise?
        _LOG.debug(f'{method}: {url}')
        async with self._session.request(method=method, url=url, timeout=self.timeout,
                                         **kwargs) as resp:
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

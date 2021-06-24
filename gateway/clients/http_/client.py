import asyncio
from typing import Any, Union, Collection, Optional

import aiohttp

from ...models import (ObjType, HTTPServerConfig, HTTPSettings, ObjProperty,
                       BaseBACnetObjModel)
from ...utils import get_file_logger

_LOG = get_file_logger(name=__name__)
# _base_path = Path(__file__).resolve().parent.parent.parent

# aliases
VisioBASGateway = Any  # '...gateway_loop.VisioBASGateway'


class VisioHTTPClient:
    """Control interactions via HTTP."""

    _URL_LOGIN = '{base_url}/auth/rest/login'
    _URL_LOGOUT = '{base_url}/auth/secure/logout'
    _URL_GET = '{base_url}/vbas/gate/get/{device_id}/{object_type_dashed}'
    _URL_POST_LIGHT = '{base_url}/vbas/gate/light/{device_id}'
    _URL_POST_PROPERTY = '{base_url}/vbas/arm/saveObjectParam/{property_id}/{replaced_object_name}'

    def __init__(self, gateway: 'VisioBASGateway', settings: HTTPSettings):
        self.gateway = gateway
        self._settings = settings
        self._timeout = aiohttp.ClientTimeout(total=settings.timeout)
        self._session = aiohttp.ClientSession(timeout=self._timeout)

        # self._upd_task = None
        self._authorized = False
        # self._stopped = False

    def __repr__(self) -> str:
        return self.__class__.__name__

    @property
    def is_authorized(self) -> bool:
        return self._authorized

    @property
    def retry_delay(self) -> int:
        return self._settings.retry

    @property
    def server_get(self) -> HTTPServerConfig:
        return self._settings.server_get

    @property
    def servers_post(self) -> list[HTTPServerConfig]:
        return self._settings.servers_post

    async def setup(self) -> None:
        """Wait for authorization then spawn a periodic update task."""
        await self.wait_login(retry=self.retry_delay)

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

    # async def post_gateway_address(self, dev_obj: BACnetDevice) -> None:
    #     """Post gateway address to polling device.
    #
    #     Args:
    #         dev_obj: Polling device object

    #     DEPRECATED
    #     """
    #     # fixme import replace to ''
    #     await self.post_property(value={'gtw_address': str(self.gateway.address)},
    #                              property_=ObjProperty.deviceAddressBinding,
    #                              obj=dev_obj,
    #                              servers=self.servers_post)

    async def get_objs(self, dev_id: int, obj_types: Collection[ObjType]
                       ) -> tuple[Union[Any, Exception], ...]:
        """Requests objects of provided type.

        If one of requests failed - return error with responses.

        Args:
            dev_id: device identifier
            obj_types: types of objects

        Returns:
            If provided one type - returns objects of this type or exception.
            If provided several types - returns tuple of objects, exceptions.
        """
        rq_tasks = [self.request(method='GET',
                                 url=self._URL_GET.format(
                                 base_url=self.server_get.current_url,
                                 device_id=str(dev_id),
                                 object_type_dashed=obj_type.name_dashed),
                                 headers=self.server_get.auth_headers)
                    for obj_type in obj_types]
        data = await asyncio.gather(*rq_tasks, return_exceptions=True)

        return data
        # return data[0] if len(obj_types) == 1 else data

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

        _LOG.debug('Logging out', extra={'servers': servers})
        try:
            logout_tasks = [self.request(method='GET',
                                         url=self._URL_LOGOUT.format(
                                         base_url=server.current_url),
                                         headers=server.auth_headers)
                            for server in servers]
            res = await asyncio.gather(*logout_tasks)

            # clear auth data
            [server.clear_auth_data() for server in servers]

            _LOG.info('Logged out',
                      extra={'servers': servers, 'result': res})
            return True

        except aiohttp.ClientResponseError as e:
            _LOG.warning('Failure logout', extra={'exc': e, })
            return False
        except Exception as e:
            _LOG.exception('Logout error:', extra={'exc': e, })
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
        """
        _LOG.debug('Logging in to servers',
                   extra={'server_get': get_server, 'servers_post': post_servers})

        res = await asyncio.gather(
            self._login_server(server=get_server),
            *[self._login_server(server=server) for server in post_servers]
        )
        is_get_authorized = res[0]  # always one instance of get server -> [0]
        is_post_authorized = any(res[1:])
        successfully_authorized = bool(is_get_authorized and is_post_authorized)

        if successfully_authorized:
            _LOG.info('Successfully authorized')
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
        """
        _LOG.debug('Perform authorization', extra={'server': server})
        try:

            while not server.is_authorized:  # and server.switch_server():
                auth_data = await self.request(method='POST',
                                               url=self._URL_LOGIN.format(
                                               base_url=server.current_url),
                                               json=server.auth_payload)
                server.set_auth_data(**auth_data)

                if not server.switch_current():
                    break

            if server.is_authorized:
                _LOG.info('Successfully authorized', extra={'server': server})
            else:
                _LOG.warning('Failed authorization', extra={'server': server})
        except aiohttp.ClientError as e:
            _LOG.warning('Failed authorization',
                         extra={'url': server.current_url, 'exc': e, })
        except Exception as e:
            _LOG.exception('Failed authorization to  {server}: {e}',
                           extra={'url': server.current_url, 'exc': e, })
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
                self.request(method='POST',
                             url=self._URL_POST_LIGHT.format(
                             base_url=server.current_url,
                             device_id=str(dev_id)),
                             headers=server.auth_headers,
                             data=data)
                for server in servers
            ]
            await asyncio.gather(*post_tasks)  # , return_exceptions=True)
            # TODO: What we should do with errors?

        except (asyncio.TimeoutError, aiohttp.ClientError,
                ConnectionError) as e:
            _LOG.warning('Failed to send', extra={'device_id': dev_id, 'exc': e, })
            return False

        except Exception as e:
            _LOG.exception('Unhandled failed to send',
                           extra={'device_id': dev_id, 'exc': e, })
            return False
        else:
            _LOG.debug('Successfully sent data',
                       extra={'device_id': dev_id, 'servers': servers})
            return True

    async def post_property(self, value: Any,
                            property_: ObjProperty, obj: BaseBACnetObjModel,
                            servers: Collection[HTTPServerConfig],
                            ) -> bool:
        try:
            post_tasks = [
                self.request(method='POST',
                             url=self._URL_POST_PROPERTY.format(
                             base_url=server.current_url,
                             property_id=property_.id_str,
                             replaced_object_name=obj.replaced_name),
                             headers=server.auth_headers,
                             data=value)
                for server in servers
            ]
            await asyncio.gather(*post_tasks)

        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            _LOG.warning('Failed to send property',
                         extra={'device_id': obj.device_id, 'property': property_,
                                'value': value, 'servers': servers, 'exc': e, })
            return False
        except Exception as e:
            _LOG.exception('Unhandled failed to send property',
                           extra={'device_id': obj.device_id, 'property': property_,
                                  'value': value, 'servers': servers, 'exc': e, })
            return False
        else:
            _LOG.debug('Successfully sent property',
                       extra={'device_id': obj.device_id, 'property': property_,
                              'value': value, 'servers': servers, })
            return True

    async def request(self, method: str, url: str, **kwargs) -> Union[list, dict]:
        """Perform HTTP request and check response.
        :return: extracted data
        """
        # todo: need re-raise?
        _LOG.debug('Perform request',
                   extra={'method': method, 'url': url, 'data': kwargs.get('data')})
        async with self._session.request(method=method, url=url, timeout=self._timeout,
                                         **kwargs) as resp:
            data = await self._extract_response_data(response=resp)
            return data

    @staticmethod
    async def _extract_response_data(response: aiohttp.ClientResponse) -> list or dict:
        """Checks the correctness of the response.
        :param response: server's response
        :return: response['data'] field after checks
        """
        response.raise_for_status()

        if response.status == 200:
            response.raise_for_status()
            _json = await response.json()
            if _json['success']:
                _LOG.debug('Successfully response',
                           extra={'url': response.url})
                try:
                    return _json['data']
                except LookupError as e:
                    # fixme
                    _LOG.warning(f'Data extracting failed (most likely in logout)')  # ,
                    # extra={'exc': e, })
            else:
                raise aiohttp.ClientError(f'Failure response: {response.url}\n{_json}')
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


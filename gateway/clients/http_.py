import asyncio
from http import HTTPStatus
from typing import Any, Union, Collection, Optional

import aiohttp

from ..models import (ObjType, HTTPServerConfig, HTTPSettings, ObjProperty,
                      BaseBACnetObjModel)
from ..utils import get_file_logger

_LOG = get_file_logger(name=__name__)


class VisioHTTPClient:
    """Control interactions via HTTP."""

    _URL_LOGIN = '{base_url}/auth/rest/login'
    _URL_LOGOUT = '{base_url}/auth/secure/logout'
    _URL_GET = '{base_url}/vbas/gate/get/{device_id}/{object_type_dashed}'
    _URL_POST_LIGHT = '{base_url}/vbas/gate/light/{device_id}'
    _URL_POST_PROPERTY = '{base_url}/vbas/arm/saveObjectParam/{property_id}/{replaced_object_name}'

    def __init__(self, gateway, settings: HTTPSettings):
        self._gtw = gateway
        self._settings = settings
        self._timeout = aiohttp.ClientTimeout(total=settings.timeout)
        self._session = aiohttp.ClientSession(timeout=self._timeout)

        self._authorized = False

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

    async def get_objects(self, dev_id: int, obj_types: Collection[ObjType]
                          ) -> tuple[Union[Any, Exception], ...]:
        """Requests objects of provided type.

        If one of requests failed - return error with responses.

        Args:
            dev_id: device identifier
            obj_types: types of objects

        Returns:
            Tuple of objects and exceptions (if they raised).
        """
        get_tasks = [
            self.request(method='GET',
                         url=self._URL_GET.format(
                             base_url=self.server_get.current_url,
                             device_id=str(dev_id),
                             object_type_dashed=obj_type.name_dashed),
                         headers=self.server_get.auth_headers,
                         extract_data=True
                         ) for obj_type in obj_types
        ]
        extracted_data = await asyncio.gather(*get_tasks, return_exceptions=True)
        # for resp in asyncio.as_completed(asyncio.gather(*rq_tasks)):
        #     await self.async_extract_response_data(resp=await resp)
        #     ...

        # extracted_objs_by_type = [
        #     await self.async_extract_response_data(resp=await resp) for resp in
        #     asyncio.as_completed(asyncio.gather(*get_tasks))
        # ]
        return extracted_data

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
            logout_tasks = [
                self.request(method='GET',
                             url=self._URL_LOGOUT.format(base_url=server.current_url),
                             headers=server.auth_headers,
                             raise_for_status=True
                             ) for server in servers
            ]
            await asyncio.gather(*logout_tasks)

            # Clear auth data.
            [server.clear_auth_data() for server in servers]
            self._authorized = False

            _LOG.info('Logged out', extra={'servers': servers, })
            return True

        except (aiohttp.ClientError, Exception) as e:
            _LOG.warning('Failure logout', extra={'exc': e, })
            return False

    async def wait_login(self, retry: int = 60) -> None:
        """Ensures the authorization.

        # TODO: add backoff

        Args:
            retry: Time to sleep after failed authorization before next attempt
        """
        while not self._authorized:
            self._authorized = await self.login(get_server=self.server_get,
                                                post_servers=self.servers_post)
            if not self._authorized:
                await asyncio.sleep(delay=retry)

    async def login(self, get_server: HTTPServerConfig,
                    post_servers: Collection[HTTPServerConfig]) -> bool:
        """Perform authorization to all servers, required for work.

        Args:
            get_server: Server to send GET requests
            post_servers: Servers to send POST requests

        Returns:
            True: Can continue with current authorizations.
            False: Cannot continue.
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
        """Perform authorization to server (primary server or mirror).

        If authorization is not performed to primary server -
        switches to mirrors while authorization passed or no more mirrors.

        Args:
            server: Server to authorize.

        Returns:
            True: Server is authorized.
            False: Server is not authorized.
        """
        _LOG.debug('Perform authorization', extra={'server': server})
        try:

            while not server.is_authorized:
                try:
                    auth_data = await self.request(
                        method='POST',
                        url=self._URL_LOGIN.format(base_url=server.current_url),
                        json=server.auth_payload,
                        extract_data=True
                    )
                    # auth_data = await self.async_extract_response_data(resp=auth_resp)
                    server.set_auth_data(**auth_data)

                except (aiohttp.ClientError, Exception) as e:
                    _LOG.warning('Failed authorization',
                                 extra={'url': server.current_url, 'exc': e, })

                if not server.switch_current():
                    break

            if server.is_authorized:
                _LOG.info('Successfully authorized', extra={'server': server})
            else:
                raise aiohttp.ClientError(
                    'Authorizations on primary and mirror servers are failed'
                )

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
            POST request is successful.
        """
        try:
            post_tasks = [
                self.request(method='POST',
                             url=self._URL_POST_LIGHT.format(
                                 base_url=server.current_url,
                                 device_id=str(dev_id)),
                             headers=server.auth_headers,
                             data=data,
                             extract_data=True
                             ) for server in servers
            ]
            await asyncio.gather(*post_tasks)
            # TODO: What we should do with failed data?

            # failed_data = [
            #     await self.async_extract_response_data(resp=await resp) for resp in
            #     asyncio.as_completed(asyncio.gather(*post_tasks))
            # ]

        except (asyncio.TimeoutError, aiohttp.ClientError,
                ConnectionError, Exception) as e:
            _LOG.warning('Failed to send', extra={'device_id': dev_id, 'exc': e, })
            return False
        else:
            _LOG.debug('Successfully sent data',
                       extra={'device_id': dev_id, 'servers': servers})
            return True

    async def post_property(self, value: Any,
                            property_: ObjProperty, obj: BaseBACnetObjModel,
                            servers: Collection[HTTPServerConfig],
                            ) -> bool:
        """TODO: DO NOT USED NOW."""
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
            # TODO: add check

        except (asyncio.TimeoutError, aiohttp.ClientError, Exception) as e:
            _LOG.warning('Failed to send property',
                         extra={'device_id': obj.device_id, 'property': property_,
                                'value': value, 'servers': servers, 'exc': e, })
            return False
        else:
            _LOG.debug('Successfully sent property',
                       extra={'device_id': obj.device_id, 'property': property_,
                              'value': value, 'servers': servers, })
            return True

    async def request(self, method: str, url: str,
                      *,
                      extract_data: bool = False, **kwargs
                      ) -> Union[aiohttp.ClientResponse, Union[dict, list]]:
        """Performs HTTP request.

        Returns:
            Response instance.
        """
        _LOG.debug('Perform request',
                   extra={'method': method, 'url': url,
                          'data': kwargs.get('data'), 'json': kwargs.get('json'), })
        async with self._session.request(
                method=method, url=url, timeout=self._timeout, **kwargs
        ) as resp:
            if extract_data:
                return await self.async_extract_response_data(resp=resp)
            return resp

    async def async_extract_response_data(self, resp: aiohttp.ClientResponse
                                          ) -> Optional[Union[list, dict]]:
        self.__doc__ = self._extract_response_data.__doc__

        return await self._gtw.async_add_job(
            self._extract_response_data, resp
        )

    @staticmethod
    async def _extract_response_data(resp: aiohttp.ClientResponse
                                     ) -> Optional[Union[list, dict]]:
        """Checks the correctness of the response.

        Args:
            resp: Response instance.

        Returns:
            resp['data'] field if expected data.

        Raises:
            aiohttp.ClientResponseError: if response status >= 400.
            aiohttp.ClientPayloadError: if failure result of the request.
        """
        resp.raise_for_status()

        if resp.status == HTTPStatus.OK:
            json = await resp.json()
            if json.get('success'):
                _LOG.debug('Successfully response', extra={'url': resp.url, })
                return json.get('data')
            else:
                raise aiohttp.ClientPayloadError(
                    f'Failure server result: {resp.url} {json}'
                )

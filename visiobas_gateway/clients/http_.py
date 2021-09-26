import asyncio
from typing import TYPE_CHECKING, Any, Collection, Union

import aiohttp

from ..schemas import ObjType
from ..schemas.settings import HTTPServerConfig, HTTPSettings
from ..utils import get_file_logger, kebab_case, log_exceptions

if TYPE_CHECKING:
    from ..gateway import Gateway
else:
    Gateway = "Gateway"

_LOG = get_file_logger(name=__name__)


class HTTPClient:
    """HTTP client of visiobas_gateway."""

    # TODO: add decorator re-login on 401
    # TODO: refactor

    _URL_LOGIN = "{base_url}/auth/rest/login"
    _URL_LOGOUT = "{base_url}/auth/secure/logout"
    _URL_GET = "{base_url}/vbas/gate/get/{device_id}/{object_type_kebab}"
    _URL_POST_LIGHT = "{base_url}/vbas/gate/light/{device_id}"
    _URL_POST_PROPERTY = (
        "{base_url}/vbas/arm/saveObjectParam/{property_id}/{replaced_object_name}"
    )

    def __init__(self, gateway: Gateway, settings: HTTPSettings):
        self._gtw = gateway
        self._settings = settings
        self._timeout = aiohttp.ClientTimeout(total=settings.timeout)
        self._session = aiohttp.ClientSession(timeout=self._timeout)

        self._authorized = False

    def __repr__(self) -> str:
        return self.__class__.__name__

    @property
    def server_get(self) -> HTTPServerConfig:
        return self._settings.server_get

    @property
    def servers_post(self) -> list[HTTPServerConfig]:
        return self._settings.servers_post

    async def startup_tasks(self) -> None:
        """Wait for authorization."""
        await self.wait_login(next_attempt=self._settings.next_attempt)

    async def shutdown_tasks(self) -> None:
        """Perform logout."""
        await self.logout(servers=[self.server_get, *self.servers_post])

    async def get_objects(
        self, dev_id: int, obj_types: Collection[ObjType]
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
            self.request(
                method="GET",
                url=self._URL_GET.format(
                    base_url=self.server_get.get_url_str(url=self.server_get.current_url),
                    device_id=str(dev_id),
                    object_type_kebab=kebab_case(obj_type.name),
                ),
                headers=self.server_get.auth_headers,
                extract_data=True,
            )
            for obj_type in obj_types
        ]
        extracted_data = await asyncio.gather(*get_tasks, return_exceptions=True)

        return extracted_data

    @log_exceptions
    async def logout(self, servers: list[HTTPServerConfig]) -> None:
        """Performs log out from servers.

        Args:
            servers: Servers to perform logout.

        Returns:
            True: Successful logout
            False: Failed logout
        """

        _LOG.debug("Logging out", extra={"servers": servers})
        logout_tasks = [
            self.request(
                method="GET",
                url=self._URL_LOGOUT.format(
                    base_url=server.get_url_str(url=server.current_url)
                ),
                headers=server.auth_headers,
                raise_for_status=True,
            )
            for server in servers
        ]
        await asyncio.gather(*logout_tasks)

        # Clear auth data.
        for server in servers:
            server.clear_auth_data()
        self._authorized = False

        _LOG.info(
            "Logged out",
            extra={
                "servers": servers,
            },
        )

    async def wait_login(self, next_attempt: int) -> None:
        """Ensures the authorization.

        # TODO: add backoff

        Args:
            next_attempt: Time to sleep after failed authorization before next attempt.
        """
        while not self._authorized:
            self._authorized = await self.login(
                get_server=self.server_get, post_servers=self.servers_post
            )
            if not self._authorized:
                await asyncio.sleep(delay=next_attempt)

    async def login(
        self, get_server: HTTPServerConfig, post_servers: list[HTTPServerConfig]
    ) -> bool:
        """Perform authorization to all servers, required for work.

        Args:
            get_server: Server to send GET requests.
            post_servers: Servers to send POST requests.

        Returns:
            True: Can continue with current authorizations.
            False: Otherwise.
        """

        # if get_server in post_servers:
        #     post_servers.remove(get_server)
        _LOG.debug(
            "Logging in to servers",
            extra={"server_get": get_server, "servers_post": post_servers},
        )

        res = await asyncio.gather(
            self._login_server(server=get_server),
            *[self._login_server(server=server) for server in post_servers],
        )
        is_get_authorized = bool(res[0])  # First instance is always GET server. Required.
        is_post_authorized = any(res[1:])  # At lease one of POST servers required.

        if is_get_authorized and is_post_authorized:
            _LOG.info("Successfully authorized")
            return True
        _LOG.warning("Failed authorizations!")
        return False

    @log_exceptions
    async def _login_server(self, server: HTTPServerConfig) -> bool:
        """Perform authorization to server (primary server or mirrors).

        If authorization is not performed to primary server -
        switches to mirrors while authorization passed or no more mirrors.

        Args:
            server: Server to authorize.

        Returns:
            True: Server is authorized.
            False: Server is not authorized.
        """
        _LOG.debug("Perform authorization", extra={"server": server})
        for url in server.urls:
            server.current_url = url
            try:
                url_str = server.get_url_str(url=url)
                auth_data = await self.request(
                    method="POST",
                    url=self._URL_LOGIN.format(base_url=url_str),
                    json=server.auth_payload,
                    extract_data=True,
                )
                if isinstance(auth_data, dict):
                    server.set_auth_data(**auth_data)
                    _LOG.info(
                        "Successfully authorized",
                        extra={
                            "server": server.current_url,
                        },
                    )

                    return True
            except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as exc:
                _LOG.warning(
                    "Failed authorization",
                    extra={
                        "server": server,
                        "exc": exc,
                    },
                )
                continue
        return False

    @log_exceptions
    async def post_device(
        self, servers: Collection[HTTPServerConfig], dev_id: int, data: str
    ) -> None:
        """Performs POST requests with data to servers.

        Args:
            servers: servers to send POST requests to
            dev_id: device identifier
            data: body of POST request

        Returns:
            POST request is successful.
        """
        post_tasks = [
            self.request(
                method="POST",
                url=self._URL_POST_LIGHT.format(
                    base_url=server.get_url_str(url=server.current_url),
                    device_id=str(dev_id),
                ),
                headers=server.auth_headers,
                data=data,
                extract_data=True,
            )
            for server in servers
        ]
        await asyncio.gather(*post_tasks)
        _LOG.debug(
            "Successfully sent data",
            extra={
                "device_id": dev_id,
                "servers": servers,
            },
        )
        # TODO: What we should do with failed data?
        # failed_data = [
        #     await self.async_extract_response_data(resp=await resp) for resp in
        #     asyncio.as_completed(asyncio.gather(*post_tasks))
        # ]

    # @log_exceptions
    # async def post_property(
    #     self,
    #     value: Any,
    #     property_: ObjProperty,
    #     obj: BaseBACnetObj,
    #     servers: Collection[HTTPServerConfig],
    # ) -> None:
    #     """TODO: NOT USED NOW."""
    #     post_tasks = [
    #         self.request(
    #             method="POST",
    #             url=self._URL_POST_PROPERTY.format(
    #                 base_url=server.get_url_str(url=server.current_url),
    #                 property_id=str(property_.id),
    #                 replaced_object_name=obj.mqtt_topic,
    #             ),
    #             headers=server.auth_headers,
    #             data=value,
    #         )
    #         for server in servers
    #     ]
    #     await asyncio.gather(*post_tasks)
    #     # TODO: add check
    #     _LOG.debug(
    #         "Successfully sent property",
    #         extra={
    #             "device_id": obj.device_id,
    #             "property": property_,
    #             "value": value,
    #             "servers": servers,
    #         },
    #     )

    async def request(
        self,
        method: str,
        url: str,
        *,
        extract_data: bool = False,
        extract_text: bool = True,
        **kwargs: Any,
    ) -> Union[aiohttp.ClientResponse, dict, list, str]:
        """Performs HTTP request.
        Args:
            Accept same parameters as aiohttp.ClientSession.request()
            +
            extract_data: If True - returns extracted data
            extract_text: If True - returns extracted text

        # TODO: return rest + data
        Returns:
            Response instance.
        """
        _LOG.debug(
            "Perform request",
            extra={
                "method": method,
                "url": url,
                "data": kwargs.get("data"),
            },
        )
        async with self._session.request(
            method=method, url=url, timeout=self._timeout, **kwargs
        ) as resp:
            if extract_data:
                return await self.async_extract_response_data(resp=resp)
            if extract_text:
                return await resp.text()
            return resp

    async def async_extract_response_data(
        self, resp: aiohttp.ClientResponse
    ) -> Union[list, dict]:
        # self.__doc__ = self._extract_response_data.__doc__

        return await self._gtw.async_add_job(self._extract_response_data, resp)

    @staticmethod
    async def _extract_response_data(
        resp: aiohttp.ClientResponse,
    ) -> Union[list, dict]:
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

        json = await resp.json()
        if json.get("success"):
            _LOG.debug(
                "Successfully response",
                extra={
                    "url": resp.url,
                },
            )
            return json.get("data", {})
        raise aiohttp.ClientPayloadError(f"Failure server result: {resp.url} {json}")

from __future__ import annotations

import asyncio
from functools import wraps
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Iterable

import aiohttp

from ..schemas import BACnetObj, ObjType
from ..schemas.send_methods import SendMethod
from ..schemas.settings import HttpServerConfig, HttpSettings
from ..utils import get_file_logger, kebab_case, log_exceptions
from .base_client import AbstractBaseClient

_LOG = get_file_logger(name=__name__)

if TYPE_CHECKING:
    from ..gateway import Gateway
else:
    Gateway = Any


class HttpClient(AbstractBaseClient):
    """HTTP client of gateway."""

    # TODO: add decorator re-login on 401
    # TODO: refactor

    _URL_LOGIN = "{base_url}/auth/rest/login"
    _URL_LOGOUT = "{base_url}/auth/secure/logout"
    _URL_GET_DEVICE_TYPE = "{base_url}/vbas/gate/get/{device_id}/{object_type_kebab}"
    _URL_POST_LIGHT = "{base_url}/vbas/gate/light/{device_id}"
    _URL_POST_PROPERTY = (
        "{base_url}/vbas/arm/saveObjectParam/{property_id}/{replaced_object_name}"
    )

    def __init__(self, gateway: Gateway, settings: HttpSettings):
        super().__init__(gateway, settings)

        self._authorized = False
        self._timeout = aiohttp.ClientTimeout(total=settings.timeout)
        self._session = aiohttp.ClientSession(timeout=self._timeout)

    def get_send_method(self) -> SendMethod:
        return SendMethod.HTTP

    @staticmethod
    def relogin_on_401(func: Callable | Callable[..., Awaitable]) -> Any:
        @wraps(func)
        async def wrapper(self: HttpClient, *args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except aiohttp.ClientResponseError as exc:
                if exc.status == 401:
                    await self.wait_login()
                    return await func(*args, **kwargs)

        return wrapper

    async def async_init_client(self, settings: HttpSettings) -> None:
        pass

    @property
    def server_get(self) -> HttpServerConfig:
        return self._settings.server_get

    @property
    def servers_post(self) -> list[HttpServerConfig]:
        return self._settings.servers_post

    async def _startup_tasks(self) -> None:
        """Wait for authorization."""
        await self.wait_login(next_attempt=self._settings.next_attempt)

    async def _shutdown_tasks(self) -> None:
        """Perform logout."""
        await self.logout(servers=[self.server_get, *self.servers_post])

    async def get_objects(
        self, dev_id: int, obj_types: Iterable[ObjType]
    ) -> tuple[Any | Exception, ...]:
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
                url=self._URL_GET_DEVICE_TYPE.format(
                    base_url=self.server_get.get_url_str(url=self.server_get.current_url),
                    device_id=str(dev_id),
                    object_type_kebab=kebab_case(obj_type.name),
                ),
                headers=self.server_get.auth_headers,
                extract_json=True,
            )
            for obj_type in obj_types
        ]
        extracted_data = await asyncio.gather(*get_tasks, return_exceptions=True)

        return extracted_data

    @log_exceptions(logger=_LOG)
    async def logout(self, servers: Iterable[HttpServerConfig]) -> None:
        """Performs log out from servers.

        Args:
            servers: Servers to perform logout.
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

        for server in servers:
            server.clear_auth_data()
        self._authorized = False
        _LOG.info("Logged out", extra={"servers": servers})

    async def wait_login(self, next_attempt: int | None = None) -> None:
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
                await asyncio.sleep(delay=next_attempt or self._settings.next_attempt)

    async def login(
        self, get_server: HttpServerConfig, post_servers: list[HttpServerConfig]
    ) -> bool:
        """Perform authorization to all servers, required for work.

        Args:
            get_server: Server to send GET requests.
            post_servers: Servers to send POST requests.

        Returns:
            True: Can continue with current authorizations.
            False: Otherwise.
        """
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

    @log_exceptions(logger=_LOG)
    async def _login_server(self, server: HttpServerConfig) -> bool:
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
            # Ignore types because always used SecretUrl
            server.current_url = url  # type: ignore
            try:
                url_str = server.get_url_str(url=url)  # type: ignore
                auth_data = await self.request(
                    method="POST",
                    url=self._URL_LOGIN.format(base_url=url_str),
                    json=server.auth_payload,
                    extract_json=True,
                )
                if isinstance(auth_data, dict):
                    server.set_auth_data(**auth_data)
                    _LOG.info(
                        "Successfully authorized",
                        extra={"server": server},
                    )
                    return True
            except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as exc:
                _LOG.warning("Failed authorization", extra={"server": server, "exc": exc})
                continue
        return False

    def objects_to_message(self, objs: Iterable[BACnetObj]) -> str:
        return "".join(
            [
                obj.to_http_str(
                    obj=obj, disabled_flags=self._settings.disabled_status_flags
                )
                for obj in objs
                if self.get_send_method() in obj.property_list.send_methods
            ]
        )

    async def send_objects(self, objs: Iterable[BACnetObj]) -> None:
        device_id = list(objs)[0].device_id
        msg = self.objects_to_message(objs=objs)
        await self.post_device(servers=self.servers_post, device_id=device_id, data=msg)

    @log_exceptions(logger=_LOG)
    async def post_device(
        self, servers: Iterable[HttpServerConfig], device_id: int, data: str
    ) -> None:
        """Performs POST requests with data to servers.

        Args:
            servers: servers to send POST requests to
            device_id: device identifier
            data: body of POST request

        Returns:
            POST request is successful.
        """
        post_tasks = [
            self.request(
                method="POST",
                url=self._URL_POST_LIGHT.format(
                    base_url=server.get_url_str(url=server.current_url),
                    device_id=str(device_id),
                ),
                headers=server.auth_headers,
                data=data,
                extract_json=True,
            )
            for server in servers
        ]
        await asyncio.gather(*post_tasks)
        _LOG.debug(
            "Successfully sent data", extra={"device_id": device_id, "servers": servers}
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

    # @relogin_on_401.__func__  # type: ignore
    async def request(
        self,
        method: str,
        url: str,
        *,
        extract_json: bool = False,
        extract_text: bool = False,
        **kwargs: Any,
    ) -> aiohttp.ClientResponse | dict | list | str:
        """Performs HTTP request.
        Args:
            Accept same parameters as aiohttp.ClientSession.request()
            +
            url:
            method:
            extract_json: If True - returns extracted data
            extract_text: If True - returns extracted text

        Returns:
            Response instance.
        """
        _LOG.debug(
            "Perform request",
            extra={"method": method, "url": url, "data": kwargs.get("data")},
        )
        async with self._session.request(
            method=method, url=url, timeout=self._timeout, **kwargs
        ) as resp:
            resp.raise_for_status()

            if extract_json:
                return await self._extract_response_data(resp=resp)
            if extract_text:
                return await resp.text()
            return resp

    @staticmethod
    async def _extract_response_data(
        resp: aiohttp.ClientResponse,
    ) -> list | dict:
        """Checks the correctness of the response from server.

        Args:
            resp: Response instance.

        Returns:
            resp['data'] field if expected data.
        """
        json = await resp.json()
        if json.get("success"):
            _LOG.debug("Successful response", extra={"url": resp.url})
            return json.get("data", {})
        raise aiohttp.ClientPayloadError(f"Failure response URL:{resp.url} json:{json}")


def process_timeout(func: Callable[..., Awaitable]) -> Any:
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except asyncio.exceptions.TimeoutError:
            _LOG.warning("Timeout")

    return wrapper

import asyncio
from typing import TYPE_CHECKING, Optional

import aiohttp_cors  # type: ignore
from aiohttp.web import Application
from aiohttp.web_runner import AppRunner, TCPSite

from ..schemas.settings import ApiSettings
from ..utils import get_file_logger
from .jsonrpc import JSON_RPC_HANDLERS

if TYPE_CHECKING:
    from ..gateway import Gateway
else:
    Gateway = "Gateway"

_LOG = get_file_logger(name=__name__)


class ApiServer:
    """VisioBAS Gateway API."""

    # TODO: add run_in_thread() method

    def __init__(self, gateway: Gateway, settings: ApiSettings):
        self._gateway = gateway
        self._settings = settings
        self._app: Optional[Application] = None
        self._stopped = asyncio.Event()

    def __repr__(self) -> str:
        return self.__class__.__name__

    # @property
    # def host(self) -> str:
    #     return self._settings.host
    #
    # @property
    # def port(self) -> int:
    #     port = self._settings.port
    #     if port is not None:
    #         return int(port)
    #     return 7070

    @property
    def handlers(
        self,
    ) -> tuple:
        return JSON_RPC_HANDLERS

    @classmethod
    def create(cls, gateway: Gateway, settings: ApiSettings) -> "ApiServer":
        api = cls(gateway=gateway, settings=settings)
        api._app = api.create_app()
        return api

    async def stop(self) -> None:
        """Stops serving API."""
        self._stopped.set()

    async def start(self) -> None:
        """Starts Gateway API until stopped."""
        if self._app is None:
            self._app = self.create_app()
        await self.run_app(
            app=self._app, host=str(self._settings.HOST), port=self._settings.PORT
        )

    def create_app(self) -> Application:
        """Creates an instance of the application.

        Returns:
            Instance of the application, ready to run.
        """
        _LOG.debug("Creating app")
        app = Application()
        app["visiobas_gateway"] = self._gateway

        # Configure default CORS settings.
        cors = aiohttp_cors.setup(
            app,
            defaults={
                "*": aiohttp_cors.ResourceOptions(
                    expose_headers="*",
                    allow_headers="*",
                    allow_methods=[
                        "POST",
                    ],
                )
            },
        )

        # Register handlers
        for handler in self.handlers:
            _LOG.debug(
                "Registering handler",
                extra={
                    "handler": handler.__name__,
                    "url": handler.URL_PATH,
                },
            )
            cors.add(app.router.add_route("*", handler.URL_PATH, handler))

        # Swagger docs
        # setup_aiohttp_apispec(app=app, title='VisioBASGateway API',
        #                       swagger_path='/', error_callback=None)
        return app

    async def run_app(
        self, app: Application, host: str = "0.0.0.0", port: int = 7070
    ) -> None:
        """Runs application and blocks until stopped.

        Args:
            app: Application instance.
            host: TCP/IP hostname to serve on.
            port: TCP/IP port to serve on.
        """
        _LOG.info(
            "Starting app",
            extra={
                "host": host,
                "port": port,
            },
        )
        runner = AppRunner(app=app)
        await runner.setup()
        site = TCPSite(runner=runner, host=host, port=port)
        await site.start()

        await self._stopped.wait()
        _LOG.debug(
            "Stopping app",
            extra={
                "host": host,
                "port": port,
            },
        )
        await runner.cleanup()


# if __name__ == "__main__":
#
#     async def main():
#         api = VisioGtwApi.create(visiobas_gateway=None, settings=ApiSettings())
#         await api.start()
#
#     asyncio.run(main())

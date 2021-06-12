from typing import Union, Any

import aiohttp_cors
from aiohttp.web_app import Application
from aiohttp_apispec import setup_aiohttp_apispec
from aiomisc import entrypoint
from aiomisc.service.aiohttp import AIOHTTPService

from .jsonrpc import JSON_RPC_HANDLERS
from ..utils import get_file_logger

_LOG = get_file_logger(name=__name__)

# Aliases
JsonRPCViewAlias = Any  # '.jsonrpc.JsonRPCView'


class VisioGtwAPI(AIOHTTPService):
    """VisioBASGateway API."""

    def __init__(self, gateway, **kwargs):
        super().__init__(**kwargs)
        self._gateway = gateway

    def __repr__(self) -> str:
        return self.__class__.__name__

    @property
    def handlers(self) -> tuple[Union[JsonRPCViewAlias,], ...]:
        return JSON_RPC_HANDLERS  # todo add rest handlers

    async def create_application(self) -> Application:
        """Creates an instance of the application, ready to run."""
        _LOG.debug('Creating app ...')

        # basic_config(level=logging.DEBUG, buffered=True)

        app = Application()
        app['gateway'] = self._gateway

        cors = aiohttp_cors.setup(app)
        # resource = cors.add(app.router.add_resource("/hello"))

        # Register handlers
        for handler in self.handlers:
            _LOG.debug('Registering handler %r as %r',
                       handler.__name__, handler.URL_PATH)

            resource = cors.add(app.router.add_resource(handler.URL_PATH))
            route = cors.add(
                resource.add_route('POST', handler), {
                    '*': aiohttp_cors.ResourceOptions(
                        allow_credentials=True,
                        expose_headers=("X-Custom-Server-Header",),
                        allow_headers=("X-Requested-With", "Content-Type"),
                        max_age=3600,
                    )
                })

            # app.router.add_route('*', handler.URL_PATH, handler)

        # Swagger docs
        setup_aiohttp_apispec(app=app, title='VisioBASGateway API',
                              swagger_path='/', error_callback=None)
        return app

    # async def start(self, app: Application, host: str, port: int) -> None:
    #     _log.info('Starting runner ...')
    #     runner = AppRunner(app=app)
    #     await runner.setup()
    #     site = TCPSite(runner=runner, host=host, port=port)
    #     await site.start()
    #
    #     wait stop() fixme
    #
    #     await runner.cleanup()


if __name__ == '__main__':
    api = VisioGtwAPI(gateway=None, host='localhost', port=7071)

    with entrypoint(api) as loop:
        loop.run_forever()

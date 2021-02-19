import logging

from aiohttp.web_app import Application
from aiohttp_apispec import setup_aiohttp_apispec
from aiomisc import entrypoint
from aiomisc.log import basic_config
from aiomisc.service.aiohttp import AIOHTTPService

from gateway.utils import get_file_logger
from .handlers import HANDLERS

_log = get_file_logger(logger_name=__name__)


class VisioGatewayApiService(AIOHTTPService):
    """Control Gateway API."""

    def __init__(self, gateway, **kwargs):
        super().__init__(**kwargs)
        self._gateway = gateway

    def __repr__(self) -> str:
        return self.__class__.__name__

    async def create_application(self) -> Application:
        """Creates an instance of the application, ready to run."""
        _log.debug('Creating app ...')

        basic_config(level=logging.DEBUG, buffered=True)

        app = Application()
        app['gateway'] = self._gateway

        # Register handlers
        for handler in HANDLERS:
            _log.debug('Registering handler %r as %r',
                       handler.__name__,
                       handler.URL_PATH
                       )
            app.router.add_route('*', handler.URL_PATH, handler)

        # Swagger docs
        setup_aiohttp_apispec(app=app, title='Gateway API', swagger_path='/',
                              error_callback=None
                              )
        return app

    # async def start(self, app: Application, host: str, port: int) -> None:
    #     _log.info('Starting runner ...')
    #     runner = AppRunner(app=app)
    #     await runner.setup()
    #     site = TCPSite(runner=runner,
    #                    host=host,
    #                    port=port
    #                    )
    #     await site.start()
    #
    #     while not self._stopped:
    #         sleep_period = self._config.get('sleep_period', 60)
    #         _log.debug(f'Sleep {sleep_period}')
    #         await sleep(sleep_period)
    #
    #     await runner.cleanup()


if __name__ == '__main__':
    api = VisioGatewayApiService(gateway=None, host='localhost', port=7071
                                 )
    with entrypoint(api) as loop:
        loop.run_forever()

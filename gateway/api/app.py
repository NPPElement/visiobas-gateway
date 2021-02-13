import asyncio
import logging
from asyncio import sleep
from threading import Thread

from aiohttp.web_app import Application
from aiohttp.web_runner import AppRunner, TCPSite
from aiohttp_apispec import setup_aiohttp_apispec
from aiomisc.log import basic_config

from gateway.api.handlers import HANDLERS
from logs import get_file_logger

_log = get_file_logger(logger_name=__name__)


class VisioGatewayApi(Thread):
    """Control Gateway API."""

    def __init__(self, gateway, config: dict):
        super().__init__()
        self.setName(name=f'{self}-Thread')
        self.setDaemon(True)

        self._config = config
        self._gateway = gateway

        self.app = self.create_app(gateway=self._gateway)

        asyncio.run(self.run_runner(app=self.app,
                                    host=self._config.get('host', 'localhost'),
                                    port=self._config.get('port', 7070)
                                    )
                    )

    @staticmethod
    def create_app(gateway) -> Application:
        """Creates an instance of the application, ready to run."""

        basic_config(level=logging.DEBUG, buffered=True)

        app = Application()
        app['gateway'] = gateway

        # Register handlers
        for handler in HANDLERS:
            _log.debug('Registering handler %r as %r', handler, handler.URL_PATH)
            app.router.add_route('*', handler.URL_PATH, handler)

        # Swagger docs
        setup_aiohttp_apispec(app=app, title='Gateway API', swagger_path='/',
                              error_callback=None
                              )
        return app

    @staticmethod
    async def run_runner(app: Application, host: str, port: int):
        runner = AppRunner(app=app)
        await runner.setup()
        site = TCPSite(runner=runner,
                       host=host,
                       port=port
                       )
        await site.start()
        await sleep(3600)


if __name__ == '__main__':
    api = VisioGatewayApi(gateway=None,
                          config={'host': 'localhost', 'port': 7070})

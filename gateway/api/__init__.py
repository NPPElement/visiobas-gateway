# sock = bind_socket(address=cfg['host'],
#                        port=cfg['port'],
#                        proto_name='http'
#                        )

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

# logging.basicConfig(level=logging.DEBUG,
#                     )


class VisioGatewayApi:
    """Control Gateway API."""

    def __init__(self, gateway, config: dict):

        self._config = config
        self._gateway = gateway

        self._host = config.get('host', 'localhost')
        self._port = config.get('port', 7070)

        self._stopped = False

        self.app = self.create_app(gateway=self._gateway)

    def __repr__(self) -> str:
        return self.__class__.__name__

    # todo stop method

    def run(self) -> None:
        """Main loop."""
        _log.info(f'Starting {self} ...')
        asyncio.run(self.run_runner(app=self.app,
                                    host=self._host,
                                    port=self._port
                                    )
                    )

    def stop(self) -> None:
        _log.info(f'Stopping {self} ...')
        self._stopped = True

    @staticmethod
    def create_app(gateway) -> Application:
        """Creates an instance of the application, ready to run."""
        _log.debug('Creating app ...')

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

    async def run_runner(self, app: Application, host: str, port: int) -> None:
        _log.info('Starting runner ...')
        runner = AppRunner(app=app)
        await runner.setup()
        site = TCPSite(runner=runner,
                       host=host,
                       port=port
                       )
        await site.start()

        while not self._stopped:
            sleep_period = self._config.get('sleep_period', 60)
            _log.debug(f'Sleep {sleep_period}')
            await sleep(sleep_period)

        await runner.cleanup()


if __name__ == '__main__':
    api = VisioGatewayApi(gateway=None,
                          config={'host': 'localhost', 'port': 7070}
                          )
    api.run()

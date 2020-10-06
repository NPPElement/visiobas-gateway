import asyncio
import json
import logging
from threading import Thread

import aiohttp

from visiobas_gateway.gateway.visio_gateway import VisioGateway


class VisioClient(Thread):
    def __init__(self, gateway: VisioGateway, config: dict):
        super().__init__()

        self._logger = logging.getLogger('VisioClient')

        self._gateway = gateway

        if config is not None:
            self._config = config
        else:
            raise ValueError(f'Config for VisioClient not found.')

        self._host = config['host']
        self._port = config['port']

        self._verify = config['ssl_verify']
        self._login = config['auth']['login']
        self._md5_pwd = config['auth']['pwd']

        self._session = None
        self._connected = False
        self._stopped = False

        self._data_to_server = []

        self._user_id = None
        self._token = None

        self.start()

    def run(self) -> None:
        # todo: Should we use one loop?

        self._logger.info('Logging in to the server...')
        while not self._stopped and not self._connected:  # LOGIN
            try:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(self._rq_login())
                loop.close()
                # fixme: How often we should login?
            except Exception as e:  # fixme: exceptions
                self._logger.error(f'Login error: {e}')
            else:
                self._logger.info('Logged in to the server')

        while not self._stopped:  # REQUEST INFO FROM SERVER
            try:
                loop = asyncio.get_event_loop()
                # todo: merge received data with current
                devices_for_connectors = loop.run_until_complete(
                    self.get_devices_for_connectors())
                loop.close()

                # todo: What is the delay?
                # await asyncio.sleep(1)

                if self._gateway:
                    self._gateway.update_info_from_server(
                        devices_for_connectors=devices_for_connectors)

                    # self._gateway.put_devices_to_connectors(
                    #     devices_for_connectors=devices_for_connectors)
            except Exception as e:  # fixme: exceptions
                self._logger.error('Error of receiving information from '
                                   f'the server about devices: {e}')

            try:  # SEND DATA TO SERVER
                pass
                # todo:send devices info
                # if you have collected enough data to send
                # send verified data to the server
            except Exception as e:  # fixme: exceptions
                self._logger.error('Error sending data to the server: {e}')
            else:
                self._logger.info('The collected information is sent to the server')
        else:
            self._logger.info('VisioClient stopped.')

    @property
    def address(self):
        return ':'.join((self._host, str(self._port)))

    def is_connected(self):
        return self._connected

    def stop(self) -> None:
        self._stopped = True
        self._logger.info('VisioClient stopped')

    async def _rq_login(self) -> None:
        """
        Request login and keep login token and user_id
        """
        url = f'{self.address}/auth/rest/login'
        data = json.dumps({
            'login': self._login,
            'password': self._md5_pwd
        })
        async with aiohttp.ClientSession() as session:
            async with session.post(url=url, data=data) as response:
                self._logger.debug(f'POST: login: {self._login}')
                resp = await response.json()

                self._token = resp['token']
                self._user_id = resp['user_id']

                self._connected = True
                self._logger.info('Client is logged into the server')

    async def _rq_devices(self) -> dict:
        """
        Request of all available devices from server
        # todo: Now only bacnet devices.
        # todo: How often we should request info from server?
        :return:
        """
        url = f'{self.address}/vbas/gate/getDevices'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url) as response:
                self._logger.debug('GET: request devices from server')
                resp = await response.json()
            self._logger.debug("Successful response to a request for "
                               f"information about devices: '{resp['success']}'")

            if resp['success'] is True:
                return resp['data']
            else:
                raise ValueError(f"Error on the server when accessing: {url}")

    async def get_devices_for_connectors(self) -> dict:
        """Updates device information for each connector"""
        # todo: for other protocols
        try:
            server_response = await self._rq_devices()

            data = {
                # fixme change to bac0 object
                'bacnet': {device['75'] for device in server_response}
            }

            return data

        except LookupError as e:
            self._logger.error('Error extracting information about '
                               f'devices by protocols: {e}')
        except Exception as e:  # fixme: exceptions
            self._logger.error('Error getting information about '
                               f'devices: {e}')
        finally:
            self._logger.info('Information for connectors has been updated.')

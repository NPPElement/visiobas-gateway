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
        self._logger.info('VisioClient started. '
                          'Connecting to server.')
        while not self._stopped and not self._connected:
            try:
                await self._rq_login()
                # fixme: How often we should login?
            except Exception as e:  # fixme: exceptions
                self._logger.error(f'Server connection error: {e}')

        while not self._stopped:
            # todo: request info about devices
            # todo: send devices info
            await asyncio.sleep(1)
            # todo:

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

    def get_devices_id_by_protocol(self) -> dict:
        """
        :return: Dict that contains a list with devices id for each protocol
        """
        # todo: for other protocols
        try:
            server_response = await self._rq_devices()

            data = {
                'bacnet': {device['75'] for device in server_response}
            }

            return data

        except LookupError as e1:
            self._logger.error('Error extracting information about '
                               f'devices by protocols: {e1}')
        except Exception as e2:  # fixme: exceptions
            self._logger.error('Error getting information about '
                               f'devices: {e2}')


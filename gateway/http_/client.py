import asyncio
from multiprocessing import SimpleQueue
from pathlib import Path
from pprint import pprint
from threading import Thread
from time import sleep
from typing import Iterable

import aiohttp

from gateway.connectors import Connector, ObjType
from gateway.http_ import VisioHTTPNode, VisioHTTPConfig
from gateway.logs import get_file_logger

_log = get_file_logger(logger_name=__name__,
                       size_bytes=50_000_000
                       )


class VisioHTTPClient(Thread):
    """Control interactions via HTTP."""

    def __init__(self, gateway, verifier_queue: SimpleQueue,
                 config: dict):
        super().__init__()

        self.setName(name=f'{self}-Thread')
        self.setDaemon(True)

        self._gateway = gateway
        self._verifier_queue = verifier_queue

        self._config = config

        self.get_node = VisioHTTPNode.create_from_dict(cfg=self._config['get_node'])

        self.post_nodes = [
            VisioHTTPNode.create_from_dict(cfg=list(node.values()).pop()) for node in
            self._config['post']
        ]

        # self.__session = None  # todo: KEEP one session
        self._is_authorized = False
        self._stopped = False

    @classmethod
    def create_from_yaml(cls, gateway, verifier_queue: SimpleQueue,
                         yaml_path: Path):
        """Create HTTP client with configuration read from YAML file."""
        import yaml

        with yaml_path.open() as cfg_file:
            http_cfg = yaml.load(cfg_file, Loader=yaml.FullLoader)

        return cls(gateway=gateway,
                   verifier_queue=verifier_queue,
                   config=http_cfg
                   )

    def run(self) -> None:
        """ Keeps the connection to the server.
        todo: Periodically update authorization (1h)
        todo: Periodically requests updates from the server. (1h)
        Sends data from connectors.
        """
        _log.info(f'{self} starting ...')
        while not self._stopped:
            try:
                asyncio.run(self.run_main_loop())
            except Exception as e:
                _log.error(f'Main loop error: {e}',
                           exc_info=True
                           )

    async def run_main_loop(self) -> None:
        """Main loop."""
        async with aiohttp.ClientSession() as session:  # todo keep one session

            # Authorize to nodes. Request data then give it to connectors.
            await self.update(session=session)

            # Receive data from verifier, then send it via HTTP
            await self.run_post_loop(queue=self._verifier_queue,
                                     post_nodes=self.post_nodes,
                                     session=session
                                     )

    async def run_post_loop(self, queue: SimpleQueue,
                            post_nodes: Iterable[VisioHTTPNode],
                            session) -> None:
        """Listen queue from verifier.
        When receive data from verifier - send it to nodes via HTTP.

        Designed as an endless loop. Can be stopped from gateway thread.
        """
        _log.info('Sending loop started')
        # Loop that receive data from verifier then send it to nodes via HTTP.
        while not self._stopped:
            try:
                device_id, device_str = queue.get()
                _log.debug('Received data from BACnetVerifier: '
                           f'Device[{device_id}]'
                           )
                # todo: change to fire and forget
                _ = await self.post_device(nodes=post_nodes,
                                           device_id=device_id,
                                           data=device_str,
                                           session=session
                                           )
            except Exception as e:
                _log.error(f"Receive or post device error: {e}",
                           exc_info=True
                           )
        else:  # received stop signal
            while self._is_authorized:
                self._is_authorized = not await self.logout(
                    nodes=[self.get_node, *self.post_nodes],
                    session=session
                )
            _log.info(f'{self} stopped.')

    def __repr__(self):
        return 'VisioHTTPClient'

    def stop(self) -> None:
        self._stopped = True
        _log.info(f'Stopping {self} ...')

    async def update(self, session) -> None:
        """Update authorizations and devices data."""
        # stop devices (send all collected data)
        self._gateway.stop_devices()  # FIXME! we shouldn't stop devices!
        # todo stop sending to http storage (HTTP_ENABLE)

        # if self._is_authorized:
        #     _ = await self.logout(nodes=[self.get_node, *self.post_nodes],
        #                           session=session
        #                           )
        # TODO read cfg from env / upd cfg

        while not self._is_authorized:
            self._is_authorized = await self.login(get_node=self.get_node,
                                                   post_nodes=self.post_nodes,
                                                   session=session
                                                   )
        # Request all devices then send data to connectors
        upd_connector_coros = [
            self.upd_connector(node=self.get_node,
                               connector=connector,
                               session=session
                               ) for connector in self._gateway.connectors.values()
        ]
        _ = await asyncio.gather(*upd_connector_coros)

    async def upd_connector(self, node: VisioHTTPNode,
                            connector: Connector,
                            session) -> bool:
        """Update all devices into connector.
        :param node:
        :param connector:
        :param session:
        :return: was update successful
        """
        try:
            upd_coros = [self.upd_device(node=node,
                                         device_id=dev_id,
                                         obj_types=connector.obj_types_to_request,
                                         connector=connector,
                                         session=session
                                         ) for dev_id in connector.address_cache_ids]

            _ = await asyncio.gather(*upd_coros)
            # todo check results
            return True

        except Exception as e:
            _log.error(f'Update {connector} error: {e}',
                       exc_info=True
                       )
            return False

    async def upd_device(self, node: VisioHTTPNode,
                         device_id: int, obj_types: Iterable[ObjType],
                         connector: Connector,
                         session) -> bool:
        """Perform request objects of each types for device by id.
        Then resend data about device to connector.
        :param node:
        :param device_id:
        :param obj_types:
        :param connector:
        :param session:
        :return: is device updated successfully
        """
        try:
            # add first type - device info, contains upd_interval
            obj_types = [ObjType.DEVICE, *obj_types]

            obj_coros = [
                self._rq(method='GET',
                         url=(f'{node.cur_server.base_url}'
                              f'/vbas/gate/get/{device_id}/{obj_type.name_dashed}'),
                         session=session,
                         headers=node.cur_server.auth_headers
                         ) for obj_type in obj_types
            ]
            objs_data = await asyncio.gather(*obj_coros)

            # objects of each type, if it's not empty, are added to the dictionary,
            # where key is obj_type and value is list with objects
            objs_data = {obj_type: objs for obj_type, objs in
                         zip(obj_types, objs_data)
                         if objs_data
                         }
            # todo: IDEA TO FUTURE: can send objects to connector by small parts
            connector.http_queue.put((device_id, objs_data))
            return True

        except Exception as e:
            _log.error(f'Device [{device_id}] updating was failed: {e}',
                       exc_info=True
                       )
            return False

    async def logout(self, nodes: Iterable[VisioHTTPNode],
                     session) -> bool:
        """Perform log out from all nodes.
        :param nodes:
        :param session:
        :return: is logout successful
        """
        logout_url = '/vdesk/secure/logout'  # todo move to class attr?
        _log.debug(f'Logout from: {nodes} ...')
        try:
            logout_coros = [self._rq(method='GET',
                                     url=node.cur_server.base_url + logout_url,
                                     session=session,
                                     headers=node.cur_server.auth_headers
                                     ) for node in nodes]
            _ = await asyncio.gather(*logout_coros)
            return True
        except Exception as e:
            _log.warning(f'Logout was failed: {e}',
                         exc_info=True
                         )
            return False

    async def login(self, get_node: VisioHTTPNode,
                    post_nodes: Iterable[VisioHTTPNode],
                    session) -> bool:
        """Perform authorization to all nodes.
        :param get_node:
        :param post_nodes:
        :param session:
        :return: can continue with current authorizations
        """
        _log.debug(f'Logging in to {get_node}, {post_nodes} ...')

        res = await asyncio.gather(self._login_node(node=get_node,
                                                    session=session
                                                    ),
                                   *[self._login_node(node=node,
                                                      session=session
                                                      ) for node in post_nodes]
                                   )
        is_get_authorized = res[0]
        is_post_authorized = any(res[1:])
        successfully_authorized = bool(is_get_authorized and is_post_authorized)

        if successfully_authorized:
            _log.info(f'Successfully authorized to {get_node}, {post_nodes}')
        else:
            _log.warning("Authorizations failed! Next attempt after "
                         f"{self._config['delay']['auth_next_attempt']} seconds."
                         )
            sleep(self._config['delay']['auth_next_attempt'])

        return successfully_authorized

    async def _login_node(self, node: VisioHTTPNode,
                          session) -> bool:
        """ Perform authorization to node (primary server + mirror)
        :param node: node on witch the authorization is performed
        :param session:
        :return: is node authorized
        """
        _log.info(f'Authorization to {node} ...')
        try:
            is_authorized = await self._login_server(server=node.cur_server,
                                                     session=session
                                                     )
            if not is_authorized:
                node.switch_to_mirror()
                is_authorized = await self._login_server(server=node.cur_server,
                                                         session=session
                                                         )
            if is_authorized:
                _log.info(f'Successfully authorized on {node}')
            else:
                _log.warning(f'Authorization on {node} failed!')
        except Exception as e:
            _log.warning(f'Authorization error! Please check {node}: {e}',
                         exc_info=True
                         )
        finally:
            return node.is_authorized

    async def _login_server(self, server: VisioHTTPConfig,
                            session) -> bool:
        """ Perform authorization to server
        :param server: server on which the authorization is performed
        :param session:
        :return: is server authorized
        """
        if server.is_authorized:
            return True

        _log.info(f'Authorization to {server} ...')
        auth_url = server.base_url + '/auth/rest/login'
        try:
            auth_data = await self._rq(method='POST',
                                       url=auth_url,
                                       json=server.auth_payload,
                                       session=session
                                       )
            server.set_auth_data(bearer_token=auth_data['token'],
                                 user_id=auth_data['user_id'],
                                 auth_user_id=auth_data['auth_user_id']
                                 )
            if server.is_authorized:
                _log.info(f'Successfully authorized on {server}')
            else:
                _log.info(f'Authorization on {server} failed!')

        except aiohttp.ClientError as e:
            _log.warning(f'Authorization on {server} was failed: {e}')
            # raise e
        except Exception as e:
            _log.error(f'Authorization error! Please check {server}: {e}',
                       exc_info=True
                       )
            # raise e
        finally:
            return server.is_authorized

    async def post_device(self, nodes: Iterable[VisioHTTPNode],
                          device_id: int, data: str, session) -> bool:
        """Perform POST requests with data to nodes.
        :param nodes:
        :param device_id:
        :param data:
        :param session:
        :return: is POST requests successful
        """
        try:
            post_coros = [self._rq(method='POST',
                                   url=(f'{node.cur_server.base_url}'
                                        f'/vbas/gate/light/{device_id}'),
                                   session=session,
                                   headers=node.cur_server.auth_headers,
                                   data=data
                                   ) for node in nodes
                          ]
            _ = await asyncio.gather(*post_coros)
            _log.debug(f'Successfully sent [{device_id}]to {nodes}')
            return True
        except Exception as e:
            _log.warning(f'Sending device error: {e}',
                         exc_info=True
                         )
            return False

    async def _rq(self, method: str, url: str, session, **kwargs) -> list or dict:
        """Perform HTTP request and check response
        :return: extracted data
        """
        # todo: need re-raise?
        _log.debug(f'{method}: {url}')
        async with session.request(method=method, url=url, **kwargs) as resp:
            data = await self._extract_response_data(response=resp)
            return data

    @staticmethod
    async def _extract_response_data(response) -> list or dict:
        """ Checks the correctness of the response.
        :param response: server's response
        :return: response['data'] field after checks
        """
        if response.status == 200:
            resp_json = await response.json()
            if resp_json['success']:
                _log.debug(f'Successfully response: {response.url}')
                return resp_json['data']
            else:
                # todo: switch to another server
                # _log.warning(f'Server returned failure response: {response.url}\n'
                #              f'{resp_json}')
                raise aiohttp.ClientError(
                    f'Failure response: {response.url}\n{resp_json}'
                )
        else:
            # todo: switch to another server
            # _log.warning('Server response status error: '
            #              f'[{response.status}] {response.url}')
            raise aiohttp.ClientError('Response status error: '
                                      f'[{response.status}] {response.url}'
                                      )

    # @staticmethod
    # async def __check_rejected(device_id: int, data: list) -> list:
    #     """ Inform about rejected objects.
    #
    #     # todo: Now the server does not always correctly return the list with errors.
    #
    #     :param data: polled by BACnet Device
    #     # :return: list of rejected by server side.
    #     """
    #     if not data:  # all object are accepted on server side
    #         _log.debug(f"POST-result: Device [{device_id}] "
    #                    "Server didn't return unaccepted objects.")
    #         return data
    #     else:
    #         rejected_objects_id = [obj[str(ObjProperty.objectIdentifier.id)] for
    #                                obj in data]
    #         _log.warning(f'POST-result: Device [{device_id}] '
    #                      'Error processing objects on '
    #                      f'the server: {rejected_objects_id}')
    #         # todo: What should we doing with rejected objects?
    #         return rejected_objects_id

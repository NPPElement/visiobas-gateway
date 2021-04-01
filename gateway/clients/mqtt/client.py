import asyncio
import uuid
from json import loads, JSONDecodeError
from logging import getLogger
from pathlib import Path
from typing import Sequence

import paho.mqtt.client as mqtt

from .api import VisioMQTTApi
from ...models import ResultCode, Qos

_log = getLogger(__name__)


class VisioMQTTClient:
    """Control interactions via MQTT."""

    def __init__(self, gateway, config: dict):
        self._gateway = gateway
        self._config = config

        self._host = config['host']
        self._port = config['port']
        self._username = config['username']
        self._password = config['password']

        self._qos = config.get('qos', Qos.AT_MOST_ONCE_DELIVERY)
        self._retain = config.get('retain', True)
        self._keepalive = config.get('keepalive', 60)

        self._stopped = False
        self._connected = False
        self._client: mqtt.Client = None
        self._paho_lock = asyncio.Lock()
        self.api = VisioMQTTApi(visio_mqtt_client=self, gateway=gateway)

        self.init_client()

    def __repr__(self) -> str:
        return self.__class__.__name__

    @property
    def topics(self) -> list[tuple[str, int]]:
        return [(topic, self._qos) for topic in self._config['subscribe']]

    @property
    def client_id(self) -> str:
        client_id = self._config.get('client_id')
        if client_id is None:
            client_id = mqtt.base62(uuid.uuid4().int, padding=22)
        return client_id

    # @property
    # def certificate(self) -> str:
    #     certificate = self._config.get('certificate')
    # self._client.tls_set_context(ssl.SSLContext(ssl.PROTOCOL_TLSv1_2))
    # self._client.tls_set()
    #     # todo add certificate

    @classmethod
    def from_yaml(cls, gateway, yaml_path: Path):
        # todo add a pydantic model of config and use it
        import yaml

        with yaml_path.open() as cfg_file:
            config = yaml.load(cfg_file, Loader=yaml.FullLoader)
            _log.info(f'Creating {cls.__name__} from {yaml_path} ...')
        return cls(gateway=gateway, config=config)

    def init_client(self) -> None:
        """Initialize MQTT client."""
        self._client = mqtt.Client(client_id=self.client_id,
                                   protocol=mqtt.MQTTv311,
                                   transport='tcp'  # todo ws?
                                   )  # todo add protocol version choice
        self._client.username_pw_set(username=self._username, password=self._password)

        # Set up external MQTT broker callbacks
        self._client.on_connect = self._on_connect_callback
        self._client.on_disconnect = self._on_disconnect_callback
        self._client.on_subscribe = self._on_subscribe_cb
        # todo unsubscribe cb
        self._client.on_message = self._on_message_cb
        self._client.on_publish = self._on_publish_cb

    # def run(self):
    #     """Main loop."""
    #     while not self._stopped:  # not self._connected and
    #         if self._connected:
    #             self._run_loop()
    #         else:
    #             try:
    #                 self.connect(host=self._host,
    #                              port=self._port
    #                              )
    #             except ConnectionRefusedError as e:
    #                 _log.warning(f'Cannot connect to broker: {e}')
    #                 time.sleep(10)
    #             except Exception as e:
    #                 _log.error(f'Connection to broker error: {e}',
    #                            exc_info=True
    #                            )

    # def _run_loop(self):
    #     """Listen queue from verifier.
    #     When receive data from verifier - publish it to MQTT.
    #
    #     Designed as an endless loop. Can be stopped from gateway thread.
    #     """
    #     # self.subscribe(topics=self.topics)
    #     while not self._stopped:
    #         try:
    #             topic, data = self._getting_queue.get()
    #             _log.debug(f'Received: {topic}: {data}')
    #
    #             self.publish(payload=data,
    #                          topic=topic,
    #                          qos=self._qos,
    #                          retain=self._retain
    #                          )
    #         except Exception as e:
    #             _log.error(f"Receive-publish error: {e}",
    #                        exc_info=True
    #                        )
    #     else:  # received stop signal
    #         _log.info(f'{self} stopped.')

    async def stop(self) -> None:
        self._stopped = True
        _log.info(f'Stopping {self} ...')
        await self.async_disconnect()

    async def connect(self, host: str, port: int = 1883) -> None:
        """Connect to the broker. Without subscriptions."""
        try:
            await self._client.connect_async(host=host, port=port)
            self._client.reconnect_delay_set()
        except OSError as e:
            _log.error(f'Failed to connect to MQTT broker {e}')
        self._client.loop_start()
        # self._client.loop_forever(retry_first_connection=True)

    async def async_disconnect(self) -> None:
        """Asynchronously call disconnect."""

        def disconnect():
            """Disconnect to broker."""
            self._client.disconnect()
            _log.debug(f'{self._client} Disconnecting to broker')
            # self._connected = False # will call in internal callback
            self._client.loop_stop()

        await self._gateway.add_job(disconnect)

    async def subscribe(self, topics: Sequence[tuple[str, int] | tuple[str, int]],
                        qos: int = Qos.AT_MOST_ONCE_DELIVERY) -> None:
        """Perform a subscription.

        Topics example:
            [("my/topic", 0), ("another/topic", 2)]
        """
        async with self._paho_lock:
            result, mid = await self._gateway.add_job(
                self._client.subscribe, topics, qos
            )
        # check will perform in internal callback
        # if result == mqtt.MQTT_ERR_SUCCESS:
        #     _log.debug(f'Subscribed to topics: {topics}')
        # elif result == mqtt.MQTT_ERR_NO_CONN:
        #     _log.warning(f'Not subscribed to topic: {topics} {result} {mid}')

    async def unsubscribe(self, topics: list[str] | str) -> None:
        """Perform an unsubscription."""
        async with self._paho_lock:
            result, mid = await self._gateway.add_job(
                self._client.unsubscribe, topics
            )
        if result == mqtt.MQTT_ERR_SUCCESS:
            _log.debug(f'Unsubscribed from topics: {topics}')
        else:
            _log.warning(f'Failed unsubscription to {topics}')

    async def publish(self, topic: str, payload: str = None,
                      qos: int = Qos.AT_MOST_ONCE_DELIVERY,
                      retain: bool = False) -> mqtt.MQTTMessageInfo:
        """Send message to the broker."""
        async with self._paho_lock:
            msg_info = await self._gateway.add_job(
                self._client.publish, topic, payload, qos, retain
            )
            return msg_info

    def _on_publish_cb(self, client, userdata, mid):
        # _log.debug(f'Published: {client} {userdata} {mid}')
        pass

    def _on_connect_callback(self, client, userdata, flags, rc, properties=None) -> None:
        if rc == ResultCode.CONNECTION_SUCCESSFUL.rc:
            self._connected = True
            _log.info('Connected to broker')
            # Subscribing in on_connect() means that if we lose the connection and
            # reconnect then subscriptions will be renewed.
            asyncio.run_coroutine_threadsafe(
                self.subscribe(topics=self.topics),
                loop=self._gateway.loop
            )
        else:
            _log.warning(f'Failed connection to broker: {ResultCode(rc)}')

    def _on_disconnect_callback(self, client, userdata, rc) -> None:
        self._connected = False
        _log.info(f'Disconnected: {ResultCode(rc)}')
        # self._client.loop_stop()

    def _on_subscribe_cb(self, userdata, mid, granted_qos, properties=None) -> None:
        if granted_qos == 128:
            _log.warning('Failed subscription')
        else:
            _log.debug('Subscribed')

    def _on_message_cb(self, client, userdata, message: mqtt.MQTTMessage) -> None:
        pass
        # msg_dct = self.decode(msg=message)
        # _log.debug(f'Received {message.topic}:{msg_dct}')
        # try:
        #     if msg_dct.get('method') == 'value':
        #         # todo: provide device_id and cache result (error) if device not polling
        #         self.api.rpc_value(params=msg_dct['params'],
        #                            topic=message.topic,
        #                            gateway=self._gateway
        #                            )
        # except Exception as e:
        #     _log.warning(f'Error: {e} :{msg_dct}',
        #                  # exc_info=True
        #                  )

    @staticmethod
    def decode(msg: mqtt.MQTTMessage) -> dict or str:
        try:
            if isinstance(msg.payload, bytes):
                content = loads(msg.payload.decode("utf-8", "ignore"))
            else:
                content = loads(msg.payload)
        except JSONDecodeError:
            if isinstance(msg.payload, bytes):
                content = msg.payload.decode("utf-8", "ignore")
            else:
                content = msg.payload
        return content

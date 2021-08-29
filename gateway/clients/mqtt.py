import asyncio
from http import HTTPStatus
from json import JSONDecodeError, dumps, loads
from typing import Sequence, Union

import paho.mqtt.client as mqtt

from ..models import MQTTSettings, Qos, ResultCode
from ..utils import get_file_logger

_LOG = get_file_logger(__name__)


class VisioMQTTClient:
    def __init__(self, gateway, settings: MQTTSettings):
        self._gtw = gateway
        self._settings = settings

        self._stopped: asyncio.Event = None
        self._connected = False
        self._client: mqtt.Client = None
        self._paho_lock = asyncio.Lock()

        self.setup()

    @classmethod
    def create(cls, gateway, settings: MQTTSettings) -> "VisioMQTTClient":
        mqtt_client = cls(gateway=gateway, settings=settings)
        mqtt_client.setup()
        return mqtt_client

    async def start(self) -> None:
        self._stopped = asyncio.Event()

        if self._client is None:
            self.setup()

        await self.connect(host=self._host, port=self._port)

    def __repr__(self) -> str:
        return self.__class__.__name__

    @property
    def _host(self) -> str:
        return self._settings.url.host

    @property
    def _port(self) -> int:
        return int(self._settings.url.port)

    @property
    def _username(self) -> str:
        return self._settings.url.user

    @property
    def _password(self) -> str:
        return self._settings.url.password

    @property
    def _qos(self) -> int:
        return int(self._settings.qos)

    @property
    def _retain(self) -> bool:
        return self._settings.retain

    @property
    def _keepalive(self) -> int:
        return self._settings.keepalive

    @property
    def topics_sub(self) -> list[tuple[str, int]]:
        """Topics to subscribe."""
        return [(topic, self._qos) for topic in self._settings.topics_sub]

    @property
    def _client_id(self) -> str:
        return self._settings.client_id

    # @property
    # def certificate(self) -> str:
    #     certificate = self._config.get('certificate')
    # self._client.tls_set_context(ssl.SSLContext(ssl.PROTOCOL_TLSv1_2))
    # self._client.tls_set()
    #     # todo add certificate

    def setup(self) -> None:
        """Initialize MQTT client."""
        self._client = mqtt.Client(
            client_id=self._client_id,
            protocol=mqtt.MQTTv311,
            transport="tcp",  # todo ws
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
        self._stopped.set()
        _LOG.info("Stopping")
        await self.async_disconnect()

    async def wait_connect(self) -> None:
        """Ensures the connection with MQTT broker."""
        while not self._connected:
            await self.connect(host=self._host, port=self._port)

    async def connect(self, host: str, port: int = 1883) -> None:
        """Connect to the broker. Without subscriptions."""
        try:
            await self._client.connect_async(
                host=host, port=port, keepalive=self._keepalive
            )
            self._client.reconnect_delay_set()
        except OSError as e:
            _LOG.warning(
                "Failed to connect to MQTT broker",
                extra={"host": host, "port": port, "exc": e},
            )
        self._client.loop_start()
        # self._client.loop_forever(retry_first_connection=True)

    async def async_disconnect(self) -> None:
        """Asynchronously call disconnect."""

        def disconnect():
            """Disconnect to broker."""
            self._client.disconnect()
            _LOG.debug("Disconnecting to broker", extra={"client": self._client})
            # self._connected = False # will call in internal callback
            self._client.loop_stop()

        await self._gtw.add_job(disconnect)

    async def subscribe(
        self, topics: Sequence[tuple[str, int]], qos: int = Qos.AT_MOST_ONCE_DELIVERY
    ) -> None:
        """Perform a subscription.

        Topics example:
            [("my/topic", 0), ("another/topic", 2)]
        """
        async with self._paho_lock:
            result, mid = await self._gtw.add_job(self._client.subscribe, topics, qos)
        # check will perform in internal callback
        # if result == mqtt.MQTT_ERR_SUCCESS:
        #     _log.debug(f'Subscribed to topics: {topics}')
        # elif result == mqtt.MQTT_ERR_NO_CONN:
        #     _log.warning(f'Not subscribed to topic: {topics} {result} {mid}')

    async def unsubscribe(self, topics: Union[list[str], str]) -> None:
        """Perform an unsubscription."""
        async with self._paho_lock:
            result, mid = await self._gtw.add_job(self._client.unsubscribe, topics)
        if result == mqtt.MQTT_ERR_SUCCESS:
            _LOG.debug(f"Unsubscribed from topics: {topics}")
        else:
            _LOG.warning(f"Failed unsubscription to {topics}")

    async def publish(
        self,
        topic: str,
        payload: str = None,
        qos: int = Qos.AT_MOST_ONCE_DELIVERY,
        retain: bool = False,
    ) -> mqtt.MQTTMessageInfo:
        """Send message to the broker."""
        async with self._paho_lock:
            msg_info = await self._gtw.add_job(
                self._client.publish, topic, payload, qos, retain
            )
            return msg_info

    def _on_publish_cb(self, client, userdata, mid):
        # _log.debug(f'Published: {client} {userdata} {mid}')
        pass

    def _on_connect_callback(
        self, client, userdata, flags, rc, properties=None
    ) -> None:
        if rc == ResultCode.CONNECTION_SUCCESSFUL.rc:
            self._connected = True
            _LOG.info("Connected to broker")
            # Subscribing in on_connect() means that if we lose the connection and
            # reconnect then subscriptions will be renewed.
            asyncio.run_coroutine_threadsafe(
                self.subscribe(topics=self.topics_sub), loop=self._gtw.loop
            )
        else:
            _LOG.warning(f"Failed connection to broker: {ResultCode(rc)}")

    def _on_disconnect_callback(self, client, userdata, rc) -> None:
        self._connected = False
        _LOG.info(f"Disconnected: {ResultCode(rc)}")
        # self._client.loop_stop()

    def _on_subscribe_cb(self, userdata, mid, granted_qos, properties=None) -> None:
        if granted_qos == 128:
            _LOG.warning("Failed subscription")
        else:
            _LOG.debug("Subscribed")

    def _on_message_cb(self, client, userdata, message: mqtt.MQTTMessage) -> None:
        _LOG.debug(
            "Received message",
            extra={
                "topic": message.topic,
                "message": message,
            },
        )
        decoded_msg = self._decode(msg=message)

        if isinstance(decoded_msg, dict) and decoded_msg.get("jsonrpc") == 2.0:
            rpc_task = self._gtw.async_add_job(self.jsonrpc_over_http, decoded_msg)
            self._gtw.add_job(self._publish_rpc_response, rpc_task, message.topic)

    async def _publish_rpc_response(self, rpc_task: asyncio.Task, topic: str) -> None:
        rpc_result = await rpc_task
        await self.publish(topic=topic, payload=rpc_result)

    async def jsonrpc_over_http(self, payload: dict) -> str:
        """Performs JSON-RPC over HTTP.

        Args:
            payload:

        Returns:
            RPC Response is successful.
        """
        resp = await self._gtw.http_client.request(
            method="POST",
            url="http://127.0.0.1:7070/json-rpc",
            json=payload,
            headers="application/json",
        )
        if resp.status is HTTPStatus.OK:
            return await resp.text()
        else:
            _LOG.warning(
                "Failed JSON-RPC 2.0 over HTTP",
                extra={
                    "http_response": resp,
                },
            )
            return dumps(
                {
                    "jsonrpc": "2.0",
                    "result": {
                        "success": False,
                        "http_status": resp.status,
                    },
                }
            )

    @staticmethod
    def _decode(msg: mqtt.MQTTMessage) -> Union[dict, str]:
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

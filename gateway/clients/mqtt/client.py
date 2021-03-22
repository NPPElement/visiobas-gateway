import time
from json import loads, JSONDecodeError
from logging import getLogger
from multiprocessing import SimpleQueue
from pathlib import Path
from threading import Thread
from typing import Sequence

import paho.mqtt.client as mqtt

from .api import VisioMQTTApi
from ...models import ResultCode, Qos

_log = getLogger(__name__)


class VisioMQTTClient(Thread):
    """Control interactions via MQTT."""

    def __init__(self, gateway,
                 config: dict,
                 getting_queue: SimpleQueue = None
                 ):
        """
        :param gateway: Gateway or Panel
        """
        super().__init__()
        self.setName(name=f'{self}-Thread')
        self.setDaemon(True)

        self._gateway = gateway
        self._getting_queue = getting_queue
        self._config = config

        self._host = self._config['host']
        self._port = self._config['port']

        self._username = self._config['username']
        self._password = self._config['password']

        self._qos = self._config.get('qos', Qos.AT_MOST_ONCE_DELIVERY)
        self._retain = self._config.get('retain', True)

        self._stopped = False
        self._connected = False

        self._client = mqtt.Client(transport='tcp',
                                   # transport='websockets' # todo
                                   )
        # self._client.tls_set_context(ssl.SSLContext(ssl.PROTOCOL_TLSv1_2))
        # self._client.tls_set() # TODO
        # self._client.enable_logger()  # logger=logger
        self._client.username_pw_set(username=self._username, password=self._password)

        # Set up external MQTT broker callbacks
        self._client.on_connect = self._on_connect_cb
        self._client.on_disconnect = self._on_disconnect_cb
        self._client.on_subscribe = self._on_subscribe_cb
        self._client.on_message = self._on_message_cb
        self._client.on_publish = self._on_publish_cb

        self.api = VisioMQTTApi(visio_mqtt_client=self,
                                gateway=gateway
                                )
        self.topics = [(topic, self._qos) for topic in self._config['subscribe']]

    def __repr__(self) -> str:
        return self.__class__.__name__

    @classmethod
    def from_yaml(cls, gateway, getting_queue: SimpleQueue,
                  yaml_path: Path):
        import yaml

        with yaml_path.open() as cfg_file:
            mqtt_cfg = yaml.load(cfg_file, Loader=yaml.FullLoader)
            _log.info(f'Creating {cls.__name__} from {yaml_path} ...')
        return cls(gateway=gateway,
                   getting_queue=getting_queue,
                   config=mqtt_cfg
                   )

    def run(self):
        """Main loop."""
        while not self._stopped:  # not self._connected and
            if self._connected:
                self._run_loop()
            else:
                try:
                    self.connect(host=self._host,
                                 port=self._port
                                 )
                except ConnectionRefusedError as e:
                    _log.warning(f'Cannot connect to broker: {e}')
                    time.sleep(10)
                except Exception as e:
                    _log.error(f'Connection to broker error: {e}',
                               exc_info=True
                               )

    def _run_loop(self):
        """Listen queue from verifier.
        When receive data from verifier - publish it to MQTT.

        Designed as an endless loop. Can be stopped from gateway thread.
        """
        # self.subscribe(topics=self.topics)
        while not self._stopped:
            try:
                topic, data = self._getting_queue.get()
                _log.debug(f'Received: {topic}: {data}')

                self.publish(payload=data,
                             topic=topic,
                             qos=self._qos,
                             retain=self._retain
                             )
            except Exception as e:
                _log.error(f"Receive-publish error: {e}",
                           exc_info=True
                           )
        else:  # received stop signal
            _log.info(f'{self} stopped.')

    def stop(self) -> None:
        self._stopped = True
        _log.info(f'Stopping {self} ...')
        self.disconnect()

    def connect(self, host: str, port: int = 1883):
        """Connect to broker."""
        self._client.connect(host=host,
                             port=port,
                             )
        self._client.reconnect_delay_set()
        # self.subscribe(topics=self.topics)
        self._client.loop_forever(retry_first_connection=True)

    def disconnect(self):
        self._client.disconnect()
        _log.debug(f'{self._client} Disconnecting from broker')
        self._connected = False
        self._client.loop_stop()

    def subscribe(self, topics: Sequence[tuple[str, int]]):
        """
        Topics example:
         [("my/topic", 0), ("another/topic", 2)]
         """
        result, mid = self._client.subscribe(topic=topics)
        if result == mqtt.MQTT_ERR_SUCCESS:
            _log.debug(f'Subscribed to topics: {topics}')
        elif result == mqtt.MQTT_ERR_NO_CONN:
            _log.warning(f'Not subscribed to topic: {topics} {result} {mid}')

    def publish(self, topic: str, payload: str = None, qos: int = Qos.AT_MOST_ONCE_DELIVERY,
                retain: bool = False) -> mqtt.MQTTMessageInfo:
        return self._client.publish(topic=topic,
                                    payload=payload,
                                    qos=qos, retain=retain)

    def _on_publish_cb(self, client, userdata, mid):
        # _log.debug(f'Published: {client} {userdata} {mid}')
        pass

    def _on_connect_cb(self, client, userdata, flags, rc, properties=None):
        if rc == ResultCode.CONNECTION_SUCCESSFUL.rc:
            self._connected = True
            _log.info('Successfully connected to broker')
            self.subscribe(topics=self.topics)
            # Subscribing in on_connect() means that if we lose the connection and
            # reconnect then subscriptions will be renewed.
        else:
            _log.warning(f'Failed connection to broker: {ResultCode(rc)}')

    def _on_disconnect_cb(self, client, userdata, rc):
        # self._connected = False
        _log.warning(f'Disconnected: {ResultCode(rc)}')
        # self._client.loop_stop()

    def _on_subscribe_cb(self, userdata, mid, granted_qos, properties=None):
        try:
            if granted_qos == 128:
                _log.warning('Subscription failed')
            else:
                _log.debug('Subscription success')
        except Exception as e:
            _log.error(f'Error: {e}',
                       exc_info=True
                       )

    def _on_message_cb(self, client, userdata, message: mqtt.MQTTMessage):
        msg_dct = self.decode(msg=message)
        _log.debug(f'Received {message.topic}:{msg_dct}')
        try:
            if msg_dct.get('method') == 'value':
                # todo: provide device_id and cache result (error) if device not polling
                self.api.rpc_value(params=msg_dct['params'],
                                   topic=message.topic,
                                   gateway=self._gateway
                                   )
        except Exception as e:
            _log.warning(f'Error: {e} :{msg_dct}',
                         # exc_info=True
                         )

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
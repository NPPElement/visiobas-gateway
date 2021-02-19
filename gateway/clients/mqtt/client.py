import time
from logging import getLogger
from multiprocessing import SimpleQueue
from pathlib import Path
from threading import Thread

import paho.mqtt.client as mqtt

_log = getLogger(__name__)


class VisioMQTTClient(Thread):
    """Control interactions via MQTT."""

    def __init__(self, gateway, getting_queue: SimpleQueue,
                 config: dict):
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

        self._qos = self._config.get('qos', 0)
        self._retain = self._config.get('retain', True)

        self._stopped = False
        self._connected = False

        # self.topics_to_subscribe = [
        #     ('Site/TP-1673/Controller1', 2),
        #     ('Site/TP-1673/Controller2', 2),
        #     ('Site/TP-1673/Controller3', 2)
        # ]

        # self.__subscribed = set()

        self._client = mqtt.Client(client_id='', transport='tcp')  # create new instance
        # self._client.enable_logger()  # logger=logger
        self._client.username_pw_set(username=self._username, password=self._password)

        # Set up external MQTT broker callbacks
        self._client.on_connect = self._on_connect_cb
        self._client.on_disconnect = self.__on_disconnect_cb
        self._client.on_publish = self._on_publish_cb

        # self._client.on_message = self.__on_message_cb
        # self._client.on_subscribe = self.__on_subscribe_cb

    def __repr__(self) -> str:
        return self.__class__.__name__

    @classmethod
    def create_from_yaml(cls, gateway, getting_queue: SimpleQueue,
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
                self._run_publish_loop(queue=self._getting_queue)
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

    def _run_publish_loop(self, queue: SimpleQueue):
        """Listen queue from verifier.
        When receive data from verifier - publish it to MQTT.

        Designed as an endless loop. CAn be stopped from gateway thread.
        """
        while not self._stopped:
            try:
                topic, data = queue.get()
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
        # self.__client.loop_forever(retry_first_connection=True)
        self._client.loop_start()

    def disconnect(self):
        self._client.disconnect()
        _log.debug(f'{self._client} Disconnecting from broker')
        self._connected = False
        self._client.loop_stop()

    def publish(self, payload: str, topic: str, qos: int, retain: bool):
        return self._client.publish(topic=topic,
                                    payload=payload,
                                    qos=qos,
                                    retain=retain
                                    )

    def _on_publish_cb(self, client, userdata, mid):
        # _log.debug(f'Published: {client} {userdata} {mid}')
        pass

    def _on_connect_cb(self, client, userdata, flags, rc, properties=None):

        if rc == 0:
            self._connected = True
            _log.info('Successfully connected to broker')
            # self.__subscribe(topics=self.topics_to_subscribe)
        else:
            _log.warning(f'Failed connection to broker: rc={rc}')
        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.

    def __on_disconnect_cb(self, client, userdata, rc):
        # self._connected = False
        _log.warning(f'Disconnected {client} userdata: {userdata} rc: {rc}')

    # def __on_message_cb(self, userdata, message):
    #     print(message.topic + " " + str(message.payload))

    # def __on_subscribe_cb(self, userdata, mid, granted_qos, properties=None):
    #     try:
    #         if granted_qos == 128:
    #             _log.warning('Subscription failed')
    #         else:
    #             _log.debug('Subscription success')
    #     except Exception as e:
    #         _log.error(f'Error: {e}', exc_info=True)

    # def __subscribe(self, topics: list[tuple[str, int]]):
    #     """ Topics example:
    #      [("my/topic", 0), ("another/topic", 2)]
    #      """
    #     result, mid = self._client.subscribe(topic=topics)
    #     if result == mqtt.MQTT_ERR_SUCCESS:
    #         _log.debug(f'Subscribed to topics: {topics}')
    #     elif result == mqtt.MQTT_ERR_NO_CONN:
    #         _log.warning(f'Not subscribed to topics: {topics}')

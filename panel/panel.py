from logging import getLogger
from multiprocessing import SimpleQueue
from pathlib import Path
from time import sleep

from gateway.clients import VisioMQTTClient

_base_path = Path(__file__).resolve().parent

_log = getLogger(__name__)


class VisioPanel:
    def __init__(self):
        self.mqtt_client = VisioMQTTClient.from_yaml(
            gateway=self,  # Using panel as gateway!
            getting_queue=SimpleQueue(),
            yaml_path=_base_path / 'config/mqtt.yaml'
        )
        self.mqtt_client.start()

        self._stopped = False

    def run_loop(self):
        while not self._stopped:
            sleep(60 * 5)

    def __repr__(self) -> str:
        return self.__class__.__name__

import logging
import os
import sys
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


def main():
    _log_level = os.environ.get('LOG_LEVEL', 'DEBUG')
    _log_fmt = ('%(levelname)-8s [%(asctime)s] [%(threadName)s] %(name)s'
                '.%(funcName)s(%(lineno)d): %(message)s'
                )
    # basic_config(level=logging.DEBUG, buffered=True, flush_interval=2,
    #              # log_format=_log_fmt,
    #              stream=sys.stderr
    #              )
    logging.basicConfig(level=_log_level,
                        format=_log_fmt,
                        stream=sys.stderr
                        )

    panel = VisioPanel()
    panel.run_loop()


if __name__ == '__main__':
    main()

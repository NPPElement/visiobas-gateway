import logging
import os
import sys
from multiprocessing import SimpleQueue
from pathlib import Path
from time import sleep

from gateway.http_.client import VisioHTTPClient
from tests.modbus.server import ModbusSimulationServer

# Set logging
_log_fmt = ('%(levelname)-8s [%(asctime)s] [%(threadName)s] %(name)s'
            '.%(funcName)s(%(lineno)d): %(message)s'
            )
_log_level = os.environ.get('LOG_LEVEL', 'DEBUG')
_log = logging.getLogger(__name__)

logging.basicConfig(format=_log_fmt,
                    level=_log_level,
                    stream=sys.stdout,
                    )

_base_path = Path(__file__).resolve().parent

# TODO: Please ensure that address_cache have only one device record!
if __name__ == '__main__':
    _run_delay = 60 * 5
    http_modbus_queue = SimpleQueue()
    # The queue is not for the verifier!
    # Used to transfer data from http to modbus server.

    http_client = VisioHTTPClient.create_from_yaml(
        gateway='',
        verifier_queue=http_modbus_queue,
        yaml_path=_base_path / 'config/test-modbus-http.yaml',
        test_modbus=True
    )
    modbus_server = ModbusSimulationServer(getting_queue=http_modbus_queue)

    modbus_server.start()
    http_client.start()

    while True:
        _log.debug(f'Sleep: {_run_delay} sec')
        sleep(_run_delay)

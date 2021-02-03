from multiprocessing import SimpleQueue
from pathlib import Path

from gateway.http_.client import VisioHTTPClient

_base_path = Path(__file__).resolve().parent.parent.parent

print(_base_path)

if __name__ == '__main__':
    # TODO: Ensure that address_cache have only one device record!

    http_modbus_queue = SimpleQueue()
    # The queue is not for the verifier!
    # Used to transfer data from http to modbus server.

    http_client = VisioHTTPClient.create_from_yaml(
        gateway='',
        verifier_queue=http_modbus_queue,
        yaml_path=_base_path / 'config/http.yaml',
        test_modbus=True
    )
    modbus_server =

    http_client.start()

from threading import Thread

import asyncio

from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.server.async_io import StartTcpServer

from gateway import get_file_logger

_log = get_file_logger(logger_name=__name__,
                       size_bytes=50_000_000
                       )


class TestModbusServer(Thread):
    """Class for simulate modbus devices."""
    def __init__(self):
        super().__init__()

        self.setName(name=f'{self}-Thread')
        self.setDaemon(True)

        self._stopped = False

    def __repr__(self) -> str:
        return self.__class__.__name__

    def run(self) -> None:
        pass

    async def run_server(self):
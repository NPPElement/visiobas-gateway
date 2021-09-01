import asyncio
from multiprocessing import SimpleQueue
from threading import Thread
from time import sleep

from utils import get_file_logger
from pymodbus.datastore import (
    ModbusServerContext,
    ModbusSlaveContext,
    ModbusSparseDataBlock,
)
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.server.async_io import StartTcpServer

from gateway.models.bacnet import ObjProperty, ObjType

_log = get_file_logger(name=__name__)


class ModbusSimulationServer(Thread):
    """Class for simulate modbus devices."""

    def __init__(self, getting_queue: SimpleQueue):
        super().__init__()
        self.setName(name=f"{self}-Thread")
        self.setDaemon(True)

        self._getting_queue = getting_queue

        self._stopped = False

    def __repr__(self) -> str:
        return self.__class__.__name__

    def run(self) -> None:
        """Received device's values. After that,
        runs an asynchronous server, simulating the operation of this device.
        """
        _log.debug(f"Starting {self} ...")

        # fixme: Now gets only one device
        device_address, device_reg_values = self.run_getting_loop()

        # address, port = device_address.split(':', maxsplit=1)

        sleep(5)
        _log.debug(f"Received device data: {device_reg_values}")

        asyncio.run(
            self.run_server(  # address=address,
                # port=port,
                hr_values=device_reg_values
            )
        )

    def run_getting_loop(self) -> dict[int, int]:

        # Now gets only one device, then return his data.
        while not self._stopped:
            try:
                data = self._getting_queue.get()
                # _log.debug(f'Received from queue: {data}')

                if isinstance(data, tuple):
                    dev_id, objs_data = data
                    reg_values = self.parse_registers_values(objs_data=objs_data)
                    # return reg_values

                if isinstance(data, str):
                    # dev_address, dev_port = data.split(':', maxsplit=1)
                    # fixme: expected only one device in address_cache

                    return data, reg_values

            except Exception as e:
                _log.error(f"Received device error: {e}", exc_info=True)

    @staticmethod
    def parse_registers_values(
        objs_data: dict[ObjType, list[dict]]
    ) -> dict[int, int or float]:
        from json import loads

        objs_data.pop(ObjType.DEVICE)

        reg_values = {}

        for obj_type, obj_data in objs_data.items():
            for obj in obj_data:
                try:
                    pv = obj[str(ObjProperty.presentValue.id)]
                    if pv == "acive":
                        pv = 1
                    elif pv == "inactive":
                        pv = 0

                    modbus_props = loads(obj[str(ObjProperty.propertyList.id)])[
                        "modbus"
                    ]
                    address = modbus_props["address"]
                    reg_values[address] = pv

                except Exception as e:
                    _log.warning(
                        f"Failed extraction for {obj_type} "
                        f"{obj[str(ObjProperty.objectIdentifier.id)]}: {e}",
                        # exc_info=True
                    )
        return reg_values
        # return {i: i for i in range(666)}

    @staticmethod
    async def run_server(hr_values: dict[int, int]) -> None:  # address: str, port: int,
        """Simulation loop."""

        hr_block = ModbusSparseDataBlock(hr_values)
        store = ModbusSlaveContext(
            hr=hr_block,
            # hr=ModbusSequentialDataBlock(0, [17] * 100),
        )
        context = ModbusServerContext(slaves=store, single=True)
        identity = ModbusDeviceIdentification()
        identity.VendorName = "VisioBas"
        identity.ProductCode = ""
        identity.VendorUrl = "https://www.visiodesk.ru/"
        identity.ProductName = "Modbus Simulation"
        identity.ModelName = "Modbus Simulation"
        identity.MajorMinorRevision = "0.0.1"

        _log.info("Simulation server starting ...")
        await StartTcpServer(
            context,
            identity=identity,
            address=("0.0.0.0", 5020),
            # address, port),
            allow_reuse_address=True,
            defer_start=False,
        )

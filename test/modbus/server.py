import asyncio
from multiprocessing import SimpleQueue
from threading import Thread
from time import sleep

from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.datastore import ModbusSparseDataBlock
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.server.async_io import StartTcpServer

from gateway import get_file_logger
from gateway.models.bacnet import ObjType

_log = get_file_logger(logger_name=__name__,
                       size_bytes=50_000_000
                       )


class ModbusSimulationServer(Thread):
    """Class for simulate modbus devices."""

    def __init__(self, getting_queue: SimpleQueue):
        super().__init__()
        self.setName(name=f'{self}-Thread')
        self.setDaemon(True)

        self._getting_queue = getting_queue

        self._stopped = False

    def __repr__(self) -> str:
        return self.__class__.__name__

    def run(self) -> None:
        """Received device's values. After that,
        runs an asynchronous server, simulating the operation of this device.
        """
        _log.debug(f'Starting {self} ...')
        device_reg_values = self.run_getting_loop()  # Now gets only one device
        sleep(10)
        _log.debug(f'Received device data: {device_reg_values}')

        asyncio.run(self.run_server(hr_values=device_reg_values))

    def run_getting_loop(self) -> dict[int, int]:

        # Now gets only one device, then return his data.
        while not self._stopped:
            try:
                dev_id, objs_data = self._getting_queue.get()
                reg_values = self.parse_registers_values(objs_data=objs_data)
                return reg_values

            except Exception as e:
                _log.error(f'Received device error: {e}',
                           exc_info=True
                           )

    @staticmethod
    def parse_registers_values(objs_data: dict[ObjType, list[dict]]
                               ) -> dict[int, int or float]:

        # reg_values = {}
        #
        # for obj_type, obj_data in objs_data.items():
        #     for obj in obj_data:
        #         try:
        #             pv = obj[str(ObjProperty.presentValue.id)]
        #             address = obj[str(ObjProperty.propertyList.id)]['modbus']['address']
        #             reg_values[address] = pv
        #         except Exception as e:
        #             _log.warning(f'Failed extraction for {obj_type} '
        #                          f'{obj[str(ObjProperty.objectIdentifier.id)]}: {e}'
        #                          )
        # return reg_values
        return {i: i for i in range(666)}

    @staticmethod
    async def run_server(hr_values: dict[int, int]) -> None:

        hr_block = ModbusSparseDataBlock(hr_values)
        store = ModbusSlaveContext(hr=hr_block,
                                   # hr=ModbusSequentialDataBlock(0, [17] * 100),
                                   )
        context = ModbusServerContext(slaves=store, single=True)
        identity = ModbusDeviceIdentification()
        identity.VendorName = 'VisioBas'
        identity.ProductCode = ''
        identity.VendorUrl = 'https://www.visiodesk.ru/'
        identity.ProductName = 'Modbus Simulation'
        identity.ModelName = 'Modbus Simulation'
        identity.MajorMinorRevision = '0.0.1'
        await StartTcpServer(context, identity=identity, address=("0.0.0.0", 5020),
                             allow_reuse_address=True,
                             defer_start=False)

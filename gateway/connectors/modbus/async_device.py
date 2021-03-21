import asyncio
from logging import getLogger
from multiprocessing import SimpleQueue
from typing import Sequence, Any

from pymodbus.client.asynchronous.schedulers import ASYNC_IO
from pymodbus.client.asynchronous.tcp import AsyncModbusTCPClient

from ...models import ModbusObj


class AsyncModbusDevice:
    upd_period_factor = 0.9  # todo provide from config

    def __init__(self,
                 verifier_queue: SimpleQueue,
                 connector,
                 address: str,
                 device_id: int,
                 objects: Sequence[ModbusObj],
                 update_period: int = 10):
        self.id = device_id
        self.address, self.port = address.split(sep=':', maxsplit=1)
        self.update_period = update_period

        self._log = getLogger(name=f'{device_id}')

        self._loop, self._client = None, None
        self.read_funcs, self.write_funcs = None, None

        self._connector = connector
        self._verifier_queue = verifier_queue

        self._polling = True
        self.objects = objects

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}[{self.id}]'

    def __len__(self) -> int:
        return len(self.objects)

    def _get_client(self, host: str, port: int) -> tuple:
        """Init async modbus client."""
        loop, client = AsyncModbusTCPClient(scheduler=ASYNC_IO,
                                            host=host, port=port,
                                            retries=3,
                                            retry_on_empty=True,
                                            retry_on_invalid=True
                                            )
        if (
                client is not None and
                hasattr(client, 'protocol') and
                client.protocol is not None and
                loop is not None
        ):
            self._log.debug(f'Connected to {self}')
            return loop, client
        else:
            raise ConnectionError(f'Failed to connect to {self} '
                                  f'({self.address}:{self.port})')

    @staticmethod
    def _get_functions(client) -> tuple[dict, dict]:
        read_funcs = {
            1: client.protocol.read_coils,
            2: client.protocol.read_discrete_inputs,
            3: client.protocol.read_holding_registers,
            4: client.protocol.read_input_registers,
        }
        write_funcs = {
            5: client.protocol.write_coil,
            6: client.protocol.write_register,
            15: client.protocol.write_coils,
            16: client.protocol.write_registers,
        }
        return read_funcs, write_funcs

    async def read(self, obj: ModbusObj, unit=0x01) -> Any:
        """Read data from Modbus object."""
        # todo: set reliability in fail cases

        read_cmd_code = obj.properties.func_read
        address = obj.properties.address
        quantity = obj.properties.quantity

        if read_cmd_code not in self.read_funcs:
            raise ValueError(f'Read functions must be one from {self.read_funcs.keys()}')
        try:
            data = await self.read_funcs[read_cmd_code](address=address,
                                                        count=quantity,
                                                        unit=unit)
        except asyncio.TimeoutError as e:
            self._log.error(f'reg: {address} quantity: {quantity} '
                            f'Read Timeout: {e}')
            return 'null'
        except Exception as e:
            self._log.error(
                f'Read error from reg: {address}, quantity: {quantity} : {e}')

        else:
            if not data.isError():
                self._log.debug(f'From register: {address} read: {data.registers}')
                if quantity == 1:
                    return data.registers[0]
                return data.registers
            else:
                self._log.error(f'Received error response from {address}')
                return 'null'

    async def write(self, values, obj: ModbusObj, unit=0x01) -> None:
        """Write data to Modbus object."""
        try:
            write_cmd_code = obj.properties.func_write
            if write_cmd_code not in self.write_funcs:
                raise ValueError(f'Read functions must be one of {self.write_funcs.keys()}')
            reg_address = obj.properties.address

            rq = await self.write_funcs[write_cmd_code](reg_address,
                                                        values,
                                                        unit=unit
                                                        )
            if not rq.isError():
                self._log.debug(f'Successfully write: {reg_address}: {values}')
            else:
                self._log.warning(f'Failed write: {rq}')
                raise rq  # fixme
        except Exception as e:
            self._log.exception(e)

    async def read_send_to_verifier(self, obj: ModbusObj, queue:SimpleQueue) -> None:
        try:
            value = await self.read(obj=obj)
        except Exception as e:
            self._log.exception(e)
            # todo set reliability and etc

        # todo process vales

        # todo: add BACnet properties?
        # queue.put()

    async def poll(self, objects: Sequence[ModbusObj]) -> None:
        """ Read objects from registers in Modbus Device.
            todo Convert register values to BACnet properties.
        """
        read_requests = [self.read_send_to_verifier(obj=obj,
                                                    queue=self._verifier_queue
                                                    ) for obj in self.objects]
        await asyncio.gather(*read_requests)
        self._put_device_end_to_verifier()

    def _put_device_end_to_verifier(self) -> None:
        """device_id in queue means that device polled.
        Should send collected objects to HTTP
        """
        self._verifier_queue.put(self.id)



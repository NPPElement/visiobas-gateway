import asyncio
import struct
from typing import Any, Callable, Union, Collection, Optional

from pymodbus.bit_read_message import (ReadCoilsResponse, ReadDiscreteInputsResponse)
from pymodbus.client.asynchronous.async_io import (AsyncioModbusSerialClient,
                                                   AsyncioModbusTcpClient)
from pymodbus.client.asynchronous.schedulers import ASYNC_IO
from pymodbus.client.asynchronous.serial import AsyncModbusSerialClient
from pymodbus.client.asynchronous.tcp import AsyncModbusTCPClient
from pymodbus.exceptions import ModbusException, ModbusIOException
from pymodbus.register_read_message import (ReadHoldingRegistersResponse,
                                            ReadInputRegistersResponse)
from pymodbus.transaction import ModbusRtuFramer

from .base_modbus import BaseModbusDevice
from ..models import (BACnetDeviceObj, ModbusObj, Protocol, ModbusReadFunc, ModbusWriteFunc,
                      StatusFlags)

# aliases # TODO
# BACnetDeviceModel = Any  # ...models
VisioBASGateway = Any  # ...gateway_loop


class AsyncModbusDevice(BaseModbusDevice):

    def __init__(self, device_obj: BACnetDeviceObj, gateway: 'VisioBASGateway'):
        super().__init__(device_obj, gateway)
        self._loop: asyncio.AbstractEventLoop = None
        self._client: Union[AsyncioModbusTcpClient, AsyncioModbusSerialClient] = None

        self._lock = asyncio.Lock()

    async def create_client(self) -> None:
        """Initializes asynchronous modbus client.

        Raises:
            # ConnectionError: if client is not initialized.

        Async pymodbus not support `timeout` param. Default: 2 sec
        See: <https://github.com/riptideio/pymodbus/issues/349>
        """
        self._LOG.debug('Creating pymodbus client', extra={'device_id': self.id})
        try:
            loop = self._gateway.loop
            asyncio.set_event_loop(loop=self._gateway.loop)

            if self.protocol in {Protocol.MODBUS_TCP, Protocol.MODBUS_RTUOVERTCP}:
                framer = ModbusRtuFramer if self.protocol is Protocol.MODBUS_RTUOVERTCP else None
                self._loop, self._client = AsyncModbusTCPClient(
                    scheduler=ASYNC_IO,
                    host=str(self.address), port=self.port, framer=framer,
                    retries=self.retries, retry_on_empty=True, retry_on_invalid=True,
                    loop=loop, timeout=self.timeout
                )
            elif self.protocol is Protocol.MODBUS_RTU:
                if (
                        not self._serial_clients.get(self.serial_port)
                        or not self._serial_port_locks.get(self.serial_port)
                ):
                    self._LOG.debug('Serial port not using. Creating async client',
                                    extra={'device_id': self.id,
                                           'serial_port': self.serial_port, })

                    self._loop, self._client = AsyncModbusSerialClient(
                        scheduler=ASYNC_IO,
                        method='rtu', port=self.serial_port,
                        baudrate=self._device_obj.baudrate,
                        bytesize=self._device_obj.bytesize,
                        parity=self._device_obj.parity,
                        stopbits=self._device_obj.stopbits,
                        loop=loop, timeout=self.timeout
                    )
                    self._serial_port_locks.update({self.serial_port: asyncio.Lock()})
                    self._serial_clients.update({self.serial_port: self._client})
                elif (
                        self._serial_clients.get(self.serial_port)
                        and self._serial_port_locks.get(self.serial_port)
                ):
                    self._LOG.debug('Serial port already using. Getting client',
                                    extra={'device_id': self.id,
                                           'serial_port': self.serial_port, })
                    self._client = self._serial_clients[self.serial_port]
            else:
                raise NotImplementedError('Other methods not support yet')
        except ModbusException as e:
            self._LOG.warning('Cannot create client',
                              extra={'device_id': self.id, 'exc': e, })
        else:
            self._LOG.debug('Client created', extra={'device_id': self.id})

    def close_client(self) -> None:
        self._client.stop()
        if self.protocol is Protocol.MODBUS_RTU:
            self.__class__._serial_clients.pop(self.serial_port)
            self.__class__._serial_port_locks.pop(self.serial_port)

    @property
    def is_client_connected(self) -> bool:
        if hasattr(self._client, 'protocol') and self._client.protocol is not None:
            return True
        return False

    @property
    def lock(self) -> asyncio.Lock:
        return self._serial_port_locks.get(self.serial_port) or self._lock

    async def _poll_objects(self, objs: Collection[ModbusObj]) -> None:
        read_tasks = [self.read(obj=obj) for obj in objs]
        await asyncio.gather(*read_tasks)

    @property
    def read_funcs(self) -> dict[ModbusReadFunc, Callable]:
        return {ModbusReadFunc.READ_COILS: self._client.protocol.read_coils,
                ModbusReadFunc.READ_DISCRETE_INPUTS: self._client.protocol.read_discrete_inputs,
                ModbusReadFunc.READ_HOLDING_REGISTERS: self._client.protocol.read_holding_registers,
                ModbusReadFunc.READ_INPUT_REGISTERS: self._client.protocol.read_input_registers,
                }

    @property
    def write_funcs(self) -> dict[ModbusWriteFunc, Callable]:
        return {ModbusWriteFunc.WRITE_COIL: self._client.protocol.write_coil,
                ModbusWriteFunc.WRITE_REGISTER: self._client.protocol.write_register,
                ModbusWriteFunc.WRITE_COILS: self._client.protocol.write_coils,
                ModbusWriteFunc.WRITE_REGISTERS: self._client.protocol.write_registers,
                }

    async def read(self, obj: ModbusObj, **kwargs) -> Optional[Union[int, float]]:
        """Read data from Modbus object.

        Updates object and return value.
        """
        self._polling.wait()
        try:
            if obj.func_read is ModbusReadFunc.READ_FILE:
                raise ModbusException('func-not-support')  # todo: implement 0x14 func

            # Using lock because pymodbus doesn't handle async requests internally.
            # Maybe this will change in pymodbus v3.0.0
            async with self.lock:
                resp = await self.read_funcs[obj.func_read](address=obj.address,
                                                            count=obj.quantity,
                                                            unit=self.unit)
            if resp.isError():
                raise ModbusIOException('0x80')  # todo: resp.string

            value = await self.decode(resp=resp, obj=obj)
            obj.set_pv(value=value)
            obj.sf = StatusFlags()
            obj.reliability = None

        except (TypeError, AttributeError, ValueError,
                asyncio.TimeoutError, asyncio.CancelledError,
                ModbusException, Exception
                ) as e:
            obj.set_exc(exc=e)
            self._LOG.warning('Read error',
                              extra={'device_id': self.id, 'object_id': obj.id,
                                     'object_type': obj.type, 'register': obj.address,
                                     'quantity': obj.quantity, 'exc': e,
                                     'unreachable_in_row': obj.unreachable_in_row, })
        # except Exception as e:
        #     obj.exception = e
        #     self._LOG.exception(f'Unexpected read error: {e}',
        #                         extra={'device_id': self.id, 'object_id': obj.id,
        #                                'object_type': obj.type, 'register': obj.address,
        #                                'quantity': obj.quantity, 'exc': e, })
        else:
            return obj.pv  # return not used now. Updates object

    async def write(self, value: Union[int, float], obj: ModbusObj, **kwargs) -> None:
        """Write value to Modbus object.

        Args:
            value: Value to write
            obj: Object instance.
        """
        try:
            if obj.func_write is None:
                raise ModbusException('Object cannot be overwritten')

            payload = await self.build(value=value, obj=obj)

            if (
                    obj.func_write is ModbusWriteFunc.WRITE_REGISTER
                    and isinstance(payload, list)
            ):
                # FIXME: hotfix
                assert len(payload) == 1
                payload = payload[0]

            # Using lock because pymodbus doesn't handle async requests internally.
            # Maybe this will change in pymodbus v3.0.0

            async with self.lock:
                rq = await self.write_funcs[obj.func_write](obj.address,
                                                            payload,  # skip_encode=True,
                                                            unit=self.unit)
            if rq.isError():
                raise ModbusIOException('0x80')  # todo: resp.string

            self._LOG.debug('Successfully write',
                            extra={'device_id': self.id, 'object_id': obj.id,
                                   'object_type': obj.type, 'address': obj.address,
                                   'value': value, })

        except (ModbusException, struct.error,
                asyncio.TimeoutError, Exception
                ) as e:
            self._LOG.warning('Failed write',
                              extra={'device_id': self.id, 'object_id': obj.id,
                                     'object_type': obj.type, 'register': obj.address,
                                     'quantity': obj.quantity, 'exc': e, })
        # except Exception as e:
        #     self._LOG.exception('Unhandled error',
        #                         extra={'device_id': self.id, 'object_id': obj.id,
        #                                'object_type': obj.type, 'register': obj.address,
        #                                'quantity': obj.quantity, 'exc': e, })

    async def decode(self, resp: Union[ReadCoilsResponse,
                                       ReadDiscreteInputsResponse,
                                       ReadHoldingRegistersResponse,
                                       ReadInputRegistersResponse],
                     obj: ModbusObj) -> Union[bool, int, float]:
        """Decodes non-error response from modbus read function.

        Args:
            resp: Response instance.
            obj: Object instance.

        Returns:
            Decoded from register\bits and scaled value.
        """
        return await self._gateway.async_add_job(self._decode_response, resp, obj)

    async def build(self, value: Union[int, float], obj: ModbusObj
                    ) -> Union[int, list[Union[int, bytes, bool]]]:
        """Build payload with value.

        Args:
            value: Value to write in object.
            obj: Object instance.

        Returns:
            Built payload.
        """
        return await self._gateway.async_add_job(self._build_payload, value, obj)

import asyncio
from datetime import datetime
from ipaddress import IPv4Address
from typing import Any, Callable, Union, Collection, Optional

import aiojobs
from pymodbus.bit_read_message import (ReadCoilsResponse, ReadDiscreteInputsResponse,
                                       ReadBitsResponseBase)
from pymodbus.client.asynchronous.schedulers import ASYNC_IO
from pymodbus.client.asynchronous.serial import AsyncModbusSerialClient
from pymodbus.client.asynchronous.tcp import AsyncModbusTCPClient
from pymodbus.exceptions import ModbusException
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.register_read_message import (ReadHoldingRegistersResponse,
                                            ReadInputRegistersResponse,
                                            ReadRegistersResponseBase)
from pymodbus.transaction import ModbusRtuFramer

from ..models import (BACnetDeviceModel, ModbusObjModel, ObjType, Protocol, DataType,
                      ModbusReadFunc, ModbusWriteFunc)
from ..utils import get_file_logger

# aliases # TODO
# BACnetDeviceModel = Any  # ...models


VisioBASGateway = Any  # ...gateway_loop

_LOG = get_file_logger(name=__name__, size_mb=500)


class AsyncModbusDevice:
    # upd_period_factor = 0.9  # todo provide from config

    # creates after add ModbusRTU device to avoid attaching to a different loop
    _serial_lock: Optional[asyncio.Lock] = None

    # todo: serial port device holder

    def __init__(self, device_obj: BACnetDeviceModel,  # 'BACnetDeviceModel'
                 gateway: 'VisioBASGateway'):
        self._gateway = gateway
        self._device_obj = device_obj

        self._loop: asyncio.AbstractEventLoop = None
        self._client: Union[AsyncModbusSerialClient, AsyncModbusTCPClient] = None
        self.scheduler: aiojobs.Scheduler = None

        self._lock = asyncio.Lock()

        self._polling = True
        self._objects: dict[int, set[ModbusObjModel]] = {}  # todo hide type
        # self._poll_tasks: dict[int, asyncio.Task] = {}

        self._connected = False

    @classmethod
    async def create(cls, device_obj: BACnetDeviceModel, gateway: 'VisioBASGateway'
                     ) -> 'AsyncModbusDevice':

        dev = cls(device_obj=device_obj, gateway=gateway)
        dev.scheduler = await aiojobs.create_scheduler(close_timeout=60, limit=100)
        await dev._gateway.async_add_job(dev.create_client)
        _LOG.debug('Device created', extra={'device_id': dev.id})
        return dev

    def create_client(self) -> None:
        """Initializes asynchronous modbus client.

        Raises:
            # ConnectionError: if client is not initialized.
        """
        _LOG.debug('Creating pymodbus client', extra={'device_id': self.id})
        try:
            loop = self._gateway.loop
            asyncio.set_event_loop(loop=self._gateway.loop)

            if self.protocol in {Protocol.MODBUS_TCP, Protocol.MODBUS_RTUOVERTCP}:
                framer = ModbusRtuFramer if self.protocol is Protocol.MODBUS_RTUOVERTCP else None
                self._loop, self._client = AsyncModbusTCPClient(
                    scheduler=ASYNC_IO,
                    host=str(self.address), port=self.port,
                    framer=framer,
                    retries=self.retries,
                    retry_on_empty=True,
                    retry_on_invalid=True,
                    loop=loop,
                    timeout=self.timeout
                )
            elif self.protocol is Protocol.MODBUS_RTU:
                self._loop, self._client = AsyncModbusSerialClient(
                    scheduler=ASYNC_IO,
                    method='rtu',
                    port=self._device_obj.property_list.rtu.port,
                    baudrate=self._device_obj.property_list.rtu.baudrate,
                    bytesize=self._device_obj.property_list.rtu.bytesize,
                    parity=self._device_obj.property_list.rtu.parity,
                    stopbits=self._device_obj.property_list.rtu.stopbits,
                    loop=loop,
                    timeout=self.timeout
                )
                if not self._serial_lock:
                    self._serial_lock = asyncio.Lock()
            else:
                raise NotImplementedError('Other methods not support yet.')
        except ModbusException as e:
            _LOG.warning('Cannot create client',
                         extra={'device_id': self.id, 'exc': e, })
        else:
            _LOG.debug('Client created', extra={'device_id': self.id})

    @property
    def is_client_connected(self) -> bool:
        if hasattr(self._client, 'protocol') and self._client.protocol is not None:
            return True
        return False

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}[{self.id}]'

    def __len__(self) -> int:
        return len(self._objects)

    @property
    def address(self) -> Optional[IPv4Address]:
        return self._device_obj.property_list.address

    @property
    def port(self) -> int:
        return self._device_obj.property_list.port

    @property
    def types_to_rq(self) -> tuple[ObjType, ...]:  # todo hide type
        return self._device_obj.types_to_rq

    @property
    def id(self) -> int:
        """Device id."""
        return self._device_obj.id

    @property
    def unit(self) -> int:
        if self._device_obj.property_list.protocol in {Protocol.MODBUS_RTU,
                                                       Protocol.MODBUS_RTUOVERTCP}:
            return self._device_obj.property_list.rtu.unit
        return 0x01

    @property
    def protocol(self) -> Protocol:
        return self._device_obj.property_list.protocol

    @property
    def timeout(self) -> float:
        return self._device_obj.timeout

    @property
    def reconnect_period(self) -> int:
        return self._device_obj.property_list.reconnect_period

    @property
    def retries(self) -> int:
        return self._device_obj.retries

    def load_objects(self, objs: Collection[ModbusObjModel]) -> None:
        """Groups objects by poll period and loads them into device for polling."""
        assert len(objs)

        objs = self._sort_objects_by_period(objs=objs)
        self._objects = objs
        _LOG.debug('Objects are grouped by period and loads to the device')

    @staticmethod
    def _sort_objects_by_period(objs: Collection[ModbusObjModel]
                                ) -> dict[int, set[ModbusObjModel]]:
        """Creates dict from objects, where key is period, value is collection
        of objects with that period.

        Returns:
            dict, where key is period, value is set of objects with that period.
        """
        dct = {}
        for obj in objs:
            poll_period = obj.property_list.send_interval
            try:
                dct[poll_period].add(obj)
            except KeyError:
                dct[poll_period] = {obj}
        return dct

    async def start_periodic_polls(self) -> None:
        """Starts periodic polls for all periods."""

        if self.is_client_connected:
            for period, objs in self._objects.items():
                await self.scheduler.spawn(self.periodic_poll(objs=objs, period=period))
                # _LOG.debug('Periodic polling started',
                #            extra={'device_id': self.id, 'period': period})
        else:
            _LOG.info('`pymodbus` client is not connected. Sleeping to next try',
                      extra={'device_id': self.id,
                             'seconds_to_next_try': self.reconnect_period})
            await asyncio.sleep(delay=self.reconnect_period)
            await self._gateway.async_add_job(self.create_client)
            # self._gateway.async_add_job(self.start_periodic_polls)
            await self.scheduler.spawn(self.start_periodic_polls())

    async def periodic_poll(self, objs: set[ModbusObjModel], period: int) -> None:
        await self.scheduler.spawn(self._poll_objects(objs=objs, period=period))
        _LOG.debug(f'Periodic polling task created',
                   extra={'device_id': self.id, 'period': period})
        # await self._poll_objects(objs=objs)
        await asyncio.sleep(delay=period)

        # Period of poll may change in the polling
        await self.scheduler.spawn(
            self.periodic_poll(objs=objs, period=objs.pop().property_list.send_interval))
        # self._poll_tasks[period] = self._loop.create_task(
        #     self.periodic_poll(objs=objs, period=period))

    async def _poll_objects(self, objs: Collection[ModbusObjModel], period: int) -> None:
        """Polls objects and set new periodic job in period.

        Args:
            objs: Objects to poll
            period: Time to start new poll job.
        """
        read_tasks = [self.read(obj=obj) for obj in objs]
        _t0 = datetime.now()
        # await self.scheduler.spawn(asyncio.gather(*read_tasks))
        await asyncio.gather(*read_tasks)
        _t_delta = datetime.now() - _t0
        if _t_delta.seconds > period:
            # TODO: improve tactic
            _LOG.warning('Polling period is too short! '
                         'Requests may interfere selves. Increased to x2!',
                         extra={'device_id': self.id,
                                'period_old': period, 'period_new': period * 2})
            for obj in objs:
                obj.property_list.send_interval *= 2
        _LOG.info('Objects polled',
                  extra={'device_id': self.id, 'period': period,
                         'time_spent': _t_delta.seconds, 'objects_polled': len(objs)})
        await self._gateway.verify_objects(objs=objs)
        await self._gateway.send_objects(objs=objs)

    @property
    def read_funcs(self) -> dict[ModbusReadFunc, Callable]:
        read_funcs = {
            ModbusReadFunc.READ_COILS: self._client.protocol.read_coils,
            ModbusReadFunc.READ_DISCRETE_INPUTS: self._client.protocol.read_discrete_inputs,
            ModbusReadFunc.READ_HOLDING_REGISTERS: self._client.protocol.read_holding_registers,
            ModbusReadFunc.READ_INPUT_REGISTERS: self._client.protocol.read_input_registers,
        }
        return read_funcs

    @property
    def write_funcs(self) -> dict[ModbusWriteFunc, Callable]:
        write_funcs = {
            ModbusWriteFunc.WRITE_COIL: self._client.protocol.write_coil,
            ModbusWriteFunc.WRITE_REGISTER: self._client.protocol.write_register,
            ModbusWriteFunc.WRITE_COILS: self._client.protocol.write_coils,
            ModbusWriteFunc.WRITE_REGISTERS: self._client.protocol.write_registers,
        }
        return write_funcs

    async def read(self, obj: ModbusObjModel) -> Optional[Union[float, int, str]]:
        """Read data from Modbus object.

        Updates object and return value.
        """
        read_func = obj.property_list.modbus.func_read
        address = obj.property_list.modbus.address
        quantity = obj.property_list.modbus.quantity
        try:
            if read_func == ModbusReadFunc.READ_FILE:
                raise ModbusException('func-not-support')  # todo: implement 0x14 func

            # Using lock because pymodbus doesn't handle async requests internally.
            # Maybe this will change in pymodbus v3.0.0
            lock = self._serial_lock if self.protocol is Protocol.MODBUS_RTU else self._lock
            async with lock:
                resp = await self.read_funcs[read_func](address=address,
                                                        count=quantity,
                                                        unit=self.unit)
            if not resp.isError():
                value = await self.decode(resp=resp, obj=obj)
                obj.pv = value
            else:
                raise ModbusException('0x80-error-response')
        except (TypeError, ValueError,
                asyncio.TimeoutError, asyncio.CancelledError,
                ModbusException, Exception
                ) as e:
            obj.exception = e
            _LOG.warning('Read error',
                         extra={'device_id': self.id,
                                'register': address, 'quantity': quantity, 'exc': e, })
        except Exception as e:
            obj.exception = e
            _LOG.exception(f'Unexpected read error: {e}',
                           extra={'register': address, 'quantity': quantity, 'exc': e, })

        else:
            return obj.pv  # return not used now. Updates object

    # async def write(self, value, obj: ModbusObjModel) -> None:
    #     """Write data to Modbus object."""
    #     try:
    #         write_cmd_code = obj.property_list.modbus.func_write
    #         reg_address = obj.property_list.modbus.address
    #
    #         # encoded_value = TODO encode here
    #
    #         # Using lock because pymodbus doesn't handle async requests internally.
    #         # Maybe this will change in pymodbus v3.0.0
    #         async with self._lock:
    #             rq = await self.write_funcs[write_cmd_code.code](reg_address,
    #                                                              value,
    #                                                              unit=self.unit)
    #         if not rq.isError():
    #             self._LOG.debug(f'Successfully write: {reg_address}: {value}')
    #         else:
    #             self._LOG.warning(f'Failed write: {rq}')
    #             # raise rq  # fixme: isn't exception
    #     except Exception as e:
    #         self._LOG.exception(e)

    async def decode(self, resp: Union[ReadCoilsResponse,
                                       ReadDiscreteInputsResponse,
                                       ReadHoldingRegistersResponse,
                                       ReadInputRegistersResponse],
                     obj: ModbusObjModel) -> Union[bool, int, float]:
        """Decodes non-error response from modbus read function."""
        return await self._gateway.async_add_job(self._decode_response, resp, obj)

    def _decode_response(self, resp: Union[ReadCoilsResponse,
                                           ReadDiscreteInputsResponse,
                                           ReadHoldingRegistersResponse,
                                           ReadInputRegistersResponse],
                         obj: ModbusObjModel) -> Union[bool, int, float]:

        data_length = obj.property_list.modbus.data_length
        data_type = obj.property_list.modbus.data_type

        reg_address = obj.property_list.modbus.address
        quantity = obj.property_list.modbus.quantity

        scale = obj.property_list.modbus.scale
        offset = obj.property_list.modbus.offset

        byte_order = obj.property_list.modbus.byte_order
        word_order = obj.property_list.modbus.word_order

        bit = obj.property_list.modbus.bit

        # repack = obj.property_list.modbus.repack

        if isinstance(resp, ReadBitsResponseBase):
            data = resp.bits
            return 1 if data[0] else 0  # TODO: add support several bits?
        elif isinstance(resp, ReadRegistersResponseBase):
            data = resp.registers

            if data_type == DataType.BOOL:
                if data_length == 1:
                    return 1 if data[0] else 0
                elif bit:
                    return 1 if data[bit] else 0
                else:
                    return any(data)

            decoder = BinaryPayloadDecoder.fromRegisters(
                registers=data, byteorder=byte_order,
                wordorder=word_order)
            decode_funcs = {
                DataType.BITS: decoder.decode_bits,
                # DataType.BOOL: None,
                # DataType.STR: decoder.decode_string,
                8: {DataType.INT: decoder.decode_8bit_int,
                    DataType.UINT: decoder.decode_8bit_uint, },
                16: {DataType.INT: decoder.decode_16bit_int,
                     DataType.UINT: decoder.decode_16bit_uint,
                     DataType.FLOAT: decoder.decode_16bit_float,
                     # DataType.BOOL: None,
                     },
                32: {DataType.INT: decoder.decode_32bit_int,
                     DataType.UINT: decoder.decode_32bit_uint,
                     DataType.FLOAT: decoder.decode_32bit_float, },
                64: {DataType.INT: decoder.decode_64bit_int,
                     DataType.UINT: decoder.decode_64bit_uint,
                     DataType.FLOAT: decoder.decode_64bit_float, }
            }
            assert decode_funcs[data_length][data_type] is not None

            decoded = decode_funcs[data_length][data_type]()
            scaled = decoded * scale + offset
            _LOG.debug('Decoded',
                       extra={'reg_address': reg_address, 'quantity': quantity,
                              'value_raw': data, 'data_length': data_length,
                              'data_type': data_type,
                              'value_decoded': decoded, 'value_scaled': scaled})
            return scaled

    async def encode(self):
        pass

    def _encode_register(self):
        pass

    # @classmethod
    # def download(cls, dev_id: int) -> 'AsyncModbusDevice':
    #     """Tries to download an object of device from server.
    #     Then gets objects to poll and load them into device.
    #
    #     If fail get object from server - load it from local.
    #     """

import asyncio
from datetime import datetime
from ipaddress import IPv4Address
from typing import Any, Callable, Union, Collection, Optional

import aiojobs
from pymodbus.bit_read_message import (ReadCoilsResponse, ReadDiscreteInputsResponse,
                                       ReadBitsResponseBase)
from pymodbus.client.asynchronous.async_io import AsyncioModbusSerialClient
from pymodbus.client.asynchronous.schedulers import ASYNC_IO
from pymodbus.client.asynchronous.serial import AsyncModbusSerialClient
from pymodbus.client.asynchronous.tcp import AsyncModbusTCPClient
from pymodbus.exceptions import ModbusException
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.register_read_message import (ReadHoldingRegistersResponse,
                                            ReadInputRegistersResponse,
                                            ReadRegistersResponseBase)
from pymodbus.transaction import ModbusRtuFramer

from ..models import (BACnetDevice, BACnetObj, ModbusObj, ObjType, Protocol, DataType,
                      ModbusReadFunc, ModbusWriteFunc)
from ..utils import get_file_logger

# aliases # TODO
# BACnetDeviceModel = Any  # ...models


VisioBASGateway = Any  # ...gateway_loop


# _LOG = get_file_logger(name=__name__, size_mb=500)


class AsyncModbusDevice:
    # upd_period_factor = 0.9  # todo provide from config

    # Keys is serial port names.
    _serial_clients: dict[str: AsyncioModbusSerialClient] = {}
    _serial_locks: dict[str: asyncio.Lock] = {}

    # _creation_lock = asyncio.Lock()

    _0X80_FUNC_CODE = '0x80-error-code'

    # _serial_port_devices: Optional[
    #     dict[int, 'AsyncModbusDevice']] = {}  # key it is device id
    # _tcp_devices: Optional[dict[int, 'AsyncModbusDevice']] = {}  # key it is serial port
    #
    # def __new__(cls, *args, **kwargs):
    #     dev_obj: BACnetDeviceModel = kwargs.get('device_obj', None)
    #     _LOG.debug('Call __new__()', extra={'device_object': dev_obj})
    #
    #     if dev_obj and dev_obj.property_list.protocol is Protocol.MODBUS_RTU:
    #         serial_port = dev_obj.property_list.rtu.port
    #         if cls._serial_port_devices.get(serial_port) is None:
    #             cls._serial_port_devices[serial_port] = super().__new__(cls)
    #         return cls._serial_port_devices[serial_port]
    #     elif dev_obj and dev_obj.property_list.protocol in {Protocol.MODBUS_TCP,
    #                                                         Protocol.MODBUS_RTUOVERTCP}:
    #         if cls._tcp_devices.get(dev_obj.id, None) is None:
    #             cls._tcp_devices[dev_obj.id] = super().__new__(cls)
    #         return cls._tcp_devices[dev_obj.id]
    #     else:
    #         raise ValueError('Unhandled error!')

    def __init__(self, device_obj: BACnetDevice,  # 'BACnetDeviceModel'
                 gateway: 'VisioBASGateway'):
        self._gateway = gateway
        self._device_obj = device_obj
        self._LOG = get_file_logger(name=__name__ + str(self.id))

        self._loop: asyncio.AbstractEventLoop = None
        self._client: Union[AsyncModbusSerialClient, AsyncModbusTCPClient] = None
        self.scheduler: aiojobs.Scheduler = None

        self._lock = asyncio.Lock()

        self._polling = True
        self._objects: dict[int, set[ModbusObj]] = {}  # todo hide type

        self._connected = False

    @classmethod
    async def create(cls, device_obj: BACnetDevice, gateway: 'VisioBASGateway'
                     ) -> 'AsyncModbusDevice':
        dev = cls(device_obj=device_obj, gateway=gateway)
        dev.scheduler = await aiojobs.create_scheduler(close_timeout=60, limit=100)
        await dev._gateway.async_add_job(dev.create_client)
        # _LOG.debug('Device created', extra={'device_id': dev.id})
        return dev

    def create_client(self) -> None:
        """Initializes asynchronous modbus client.

        Raises:
            # ConnectionError: if client is not initialized.

        Async pymodbus not support `timeout` param. Default: 2 sec
        See: https://github.com/riptideio/pymodbus/issues/349
        """
        self._LOG.debug('Creating pymodbus client', extra={'device_id': self.id})
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
                if (
                        not self._serial_clients.get(self.serial_port)
                        or not self._serial_locks.get(self.serial_port)
                ):
                    self._LOG.debug('Serial port not using. Creating client',
                                    extra={'device_id': self.id,
                                           'serial_port': self.serial_port, })

                    # async with self._serial_locks[self.serial_port]:
                    self._loop, self._client = AsyncModbusSerialClient(
                        scheduler=ASYNC_IO,
                        method='rtu',
                        port=self.serial_port,
                        baudrate=self._device_obj.property_list.rtu.baudrate,
                        bytesize=self._device_obj.property_list.rtu.bytesize,
                        parity=self._device_obj.property_list.rtu.parity,
                        stopbits=self._device_obj.property_list.rtu.stopbits,
                        loop=loop,
                        timeout=self.timeout
                    )
                    self._serial_locks.update({self.serial_port: asyncio.Lock()})
                    self._serial_clients.update({self.serial_port: self._client})
                elif (
                        self._serial_clients.get(self.serial_port)
                        and self._serial_locks.get(self.serial_port)
                ):
                    self._LOG.debug('Serial port already using. Getting client',
                                    extra={'device_id': self.id,
                                           'serial_port': self.serial_port, })
                    self._client = self._serial_clients[self.serial_port]
                else:
                    raise RuntimeError('Unexpected behavior')

                self._LOG.debug('Current state of serial',
                                extra={'serial_clients_dict': self._serial_clients, })
            else:
                raise NotImplementedError('Other methods not support yet.')
        except ModbusException as e:
            self._LOG.warning('Cannot create client',
                              extra={'device_id': self.id, 'exc': e, })
        else:
            self._LOG.debug('Client created', extra={'device_id': self.id})

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
    def lock(self) -> asyncio.Lock:
        return self._serial_locks.get(self.serial_port) or self._lock

    @property
    def address(self) -> Optional[IPv4Address]:
        return self._device_obj.property_list.address

    @property
    def port(self) -> Optional[int]:
        return self._device_obj.property_list.port

    @property
    def serial_port(self) -> Optional[str]:
        """

        Returns:
            Serial port name if exists. Else None.
        """
        if self.protocol is Protocol.MODBUS_RTU:
            return self._device_obj.property_list.rtu.port

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

    @property
    def dev_obj(self) -> BACnetDevice:
        return self._device_obj

    @property
    #  todo: cache?
    def objects(self) -> set[ModbusObj]:
        return {obj for objs_set in self._objects.values() for obj in objs_set}

    def load_objects(self, objs: Collection[ModbusObj]) -> None:
        """Groups objects by poll period and loads them into device for polling."""
        assert len(objs)

        objs = self._sort_objects_by_period(objs=objs)
        self._objects = objs
        self._LOG.debug('Objects are grouped by period and loads to the device')

    @staticmethod
    def _sort_objects_by_period(objs: Collection[ModbusObj]
                                ) -> dict[int, set[ModbusObj]]:
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

    async def stop(self) -> None:
        """Waits for finish of all polling tasks with timeout, and stop polling.
        Closes client.
        """
        await self.scheduler.close()
        self._LOG.info('Device stopped', extra={'device_id': self.id})

    async def start_periodic_polls(self) -> None:
        """Starts periodic polls for all periods."""

        if self.is_client_connected:
            for period, objs in self._objects.items():
                await self.scheduler.spawn(self.periodic_poll(objs=objs, period=period))
                # self._LOG.debug('Periodic polling started',
                #            extra={'device_id': self.id, 'period': period})
        else:
            self._LOG.info('`pymodbus` client is not connected. Sleeping to next try',
                           extra={'device_id': self.id,
                                  'seconds_to_next_try': self.reconnect_period})
            await asyncio.sleep(delay=self.reconnect_period)
            await self._gateway.async_add_job(self.create_client)
            # self._gateway.async_add_job(self.start_periodic_polls)
            await self.scheduler.spawn(self.start_periodic_polls())

    async def periodic_poll(self, objs: set[ModbusObj], period: int) -> None:
        await self.scheduler.spawn(self._poll_objects(objs=objs, period=period))
        self._LOG.debug(f'Periodic polling task created',
                        extra={'device_id': self.id, 'period': period,
                               'jobs_active_count': self.scheduler.active_count,
                               'jobs_pending_count': self.scheduler.pending_count, })
        # await self._poll_objects(objs=objs)
        await asyncio.sleep(delay=period)

        # Period of poll may change in the polling
        await self.scheduler.spawn(
            self.periodic_poll(objs=objs, period=period))
        # self._poll_tasks[period] = self._loop.create_task(
        #     self.periodic_poll(objs=objs, period=period))

    async def _poll_objects(self, objs: Collection[ModbusObj], period: int) -> None:
        """Polls objects and set new periodic job in period.

        Args:
            objs: Objects to poll
            period: Time to start new poll job.
        """
        self._LOG.debug('Polling started',
                        extra={'device_id': self.id, 'period': period,
                               'objects_polled': len(objs)})
        read_tasks = [self.read(obj=obj) for obj in objs]
        _t0 = datetime.now()
        # await self.scheduler.spawn(asyncio.gather(*read_tasks))
        await asyncio.gather(*read_tasks)
        _t_delta = datetime.now() - _t0
        if _t_delta.seconds > period:
            # TODO: improve tactic
            self._LOG.warning('Polling period is too short! ',
                              # 'Requests may interfere selves. Increased to x2!',
                              extra={'device_id': self.id,
                                     # 'period_old': period, 'period_new': period * 2
                                     })
            # for obj in objs:
            #     obj.property_list.send_interval *= 2

        self._LOG.info('Objects polled',
                       extra={'device_id': self.id, 'period': period,
                              'seconds_took': _t_delta.seconds,
                              'objects_polled': len(objs)})
        await self._gateway.verify_objects(objs=objs)
        await self._gateway.send_objects(objs=objs)

        # fixme hotfix
        await self._gateway.async_add_job(
            self.clear_properties, objs
        )

    @staticmethod
    def clear_properties(objs: Collection[BACnetObj]) -> None:
        # fixme hotfix
        [obj.clear_properties() for obj in objs]

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

    async def read(self, obj: ModbusObj) -> Optional[Union[float, int]]:
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
            async with self.lock:
                resp = await self.read_funcs[read_func](address=address,
                                                        count=quantity,
                                                        unit=self.unit)
            if not resp.isError():
                value = await self.decode(resp=resp, obj=obj)
                obj.set_pv(value=value)
            else:
                raise ModbusException(self._0X80_FUNC_CODE)
        except (TypeError, AttributeError,  # ValueError
                asyncio.TimeoutError, asyncio.CancelledError,
                ModbusException,
                ) as e:
            obj.exception = e
            self._LOG.warning('Read error',
                              extra={'device_id': self.id,
                                     'register': address, 'quantity': quantity, 'exc': e, })
        except (ValueError, Exception) as e:
            obj.exception = e
            self._LOG.exception(f'Unexpected read error: {e}',
                                extra={'device_id': self.id,
                                       'register': address, 'quantity': quantity,
                                       'exc': e, })

        else:
            return obj.pv  # return not used now. Updates object

    async def write(self, value: Union[int, float], obj: ModbusObj) -> None:
        """Write data to Modbus object."""
        write_cmd_code = obj.property_list.modbus.func_write
        reg_address = obj.property_list.modbus.address
        quantity = obj.property_list.modbus.quantity
        try:
            # encoded_value = TODO encode here

            # Using lock because pymodbus doesn't handle async requests internally.
            # Maybe this will change in pymodbus v3.0.0
            async with self.lock:
                rq = await self.write_funcs[write_cmd_code.code](reg_address,
                                                                 value,
                                                                 unit=self.unit)
            if not rq.isError():
                pass  # todo: collapse
            else:
                raise ModbusException(self._0X80_FUNC_CODE)
        except ModbusException as e:
            self._LOG.warning('Failed write',
                              extra={'device_id': self.id,
                                     'register': reg_address, 'quantity': quantity,
                                     'exc': e, })
        except Exception as e:
            self._LOG.exception('Unhandled error', extra={'device_id': self.id, 'exc': e, })
        else:
            self._LOG.debug(f'Successfully write',
                            extra={'device_id': self.id, 'address': reg_address,
                                   'value': value})

    async def decode(self, resp: Union[ReadCoilsResponse,
                                       ReadDiscreteInputsResponse,
                                       ReadHoldingRegistersResponse,
                                       ReadInputRegistersResponse],
                     obj: ModbusObj) -> Union[bool, int, float]:
        """Decodes non-error response from modbus read function."""
        return await self._gateway.async_add_job(self._decode_response, resp, obj)

    # @staticmethod
    def _decode_response(self, resp: Union[ReadCoilsResponse,
                                           ReadDiscreteInputsResponse,
                                           ReadHoldingRegistersResponse,
                                           ReadInputRegistersResponse],
                         obj: ModbusObj) -> Union[bool, int, float]:

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

        # TODO: Add decode with different byteorder in bytes VisioDecoder class

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
            self._LOG.debug('Decoded',
                            extra={'device_id': obj.device_id, 'object_id': obj.id,
                                   'register_address': reg_address, 'quantity': quantity,
                                   'value_raw': data, 'data_length': data_length,
                                   'data_type': data_type, 'resolution': obj.resolution,
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

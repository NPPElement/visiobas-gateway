import asyncio
from ipaddress import IPv4Address
from typing import Any, Callable, Union, Collection, Optional
from datetime import datetime

import aiojobs
from pymodbus.client.asynchronous.schedulers import ASYNC_IO
from pymodbus.client.asynchronous.serial import AsyncModbusSerialClient
from pymodbus.client.asynchronous.tcp import AsyncModbusTCPClient
from pymodbus.constants import Endian
from pymodbus.exceptions import ModbusException
from pymodbus.payload import BinaryPayloadDecoder

from ..models import BACnetDeviceModel, ModbusObjModel, ObjType, Protocol
from ..utils import get_file_logger

# aliases # TODO
# BACnetDeviceModel = Any  # ...models


VisioBASGateway = Any  # ...gateway_loop


class AsyncModbusDevice:
    # upd_period_factor = 0.9  # todo provide from config

    def __init__(self, device_obj: BACnetDeviceModel,  # 'BACnetDeviceModel'
                 gateway: 'VisioBASGateway'):
        self._gateway = gateway
        self._device_obj = device_obj

        # self._log = getLogger(name=f'{self.id}')
        self._LOG = get_file_logger(name=str(self))

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
        dev._LOG.debug('Device created', extra={'device_id': dev.id})

        await dev._gateway.async_add_job(dev.create_client)
        return dev

    def create_client(self) -> None:
        """Initializes asynchronous modbus client.

        Raises:
            # ConnectionError: if client is not initialized.
        """
        self._LOG.debug('Creating pymodbus client', extra={'device_id': self.id})
        try:
            loop = self._gateway.loop
            asyncio.set_event_loop(loop=self._gateway.loop)

            if self.protocol is Protocol.MODBUS_TCP:
                self._loop, self._client = AsyncModbusTCPClient(
                    scheduler=ASYNC_IO,
                    host=self.address, port=self.port,
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
            else:
                raise NotImplementedError('Other methods not support yet.')
        except ModbusException as e:
            self._LOG.warning(f'Cannot create client: {e}', extra={'device_id': self.id})
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
        return self._device_obj.id

    @property
    def unit(self) -> int:
        unit = self._device_obj.property_list.rtu.unit
        if isinstance(unit, int) and not isinstance(unit, bool):
            return unit
        else:
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
        """Loads object to poll.
        Group by poll period.
        """
        objs = self._sort_objects_by_period(objs=objs)
        self._objects = objs
        self._LOG.debug('Objects to poll are loaded to device')

    # @staticmethod
    def _sort_objects_by_period(self, objs: Collection[ModbusObjModel]
                                ) -> dict[int, list[ModbusObjModel]]:
        """Creates dict from objects, where key is period, value is collection
        of objects with that period.

        Returns:
            dict, where key is period, value is collection of objects with that period.
        """
        dct = {}
        for obj in objs:
            poll_period = obj.property_list.send_interval
            try:
                dct[poll_period].append(obj)
            except KeyError:
                dct[poll_period] = [obj]
        self._LOG.debug('Objects to poll are grouped by periods')
        return dct

    @property
    def read_funcs(self) -> dict[int, Callable]:
        read_funcs = {1: self._client.protocol.read_coils,
                      2: self._client.protocol.read_discrete_inputs,
                      3: self._client.protocol.read_holding_registers,
                      4: self._client.protocol.read_input_registers, }
        return read_funcs

    @property
    def write_funcs(self) -> dict[int, Callable]:
        write_funcs = {5: self._client.protocol.write_coil,
                       6: self._client.protocol.write_register,
                       15: self._client.protocol.write_coils,
                       16: self._client.protocol.write_registers, }
        return write_funcs

    async def read(self, obj: ModbusObjModel) -> Union[float, int, str]:
        """Read data from Modbus object. Updates object and return value."""
        # todo: set reliability in fail cases

        read_cmd_code = obj.property_list.modbus.func_read
        reg_address = obj.property_list.modbus.address
        quantity = obj.property_list.modbus.quantity

        if read_cmd_code not in self.read_funcs:
            raise ValueError(f'Read functions must be one from {self.read_funcs.keys()}')
        try:
            # Using lock because pymodbus doesn't handle async requests internally.
            # Maybe this will change in pymodbus v3.0.0
            async with self._lock:
                data = await self.read_funcs[read_cmd_code.code](address=reg_address,
                                                                 count=quantity,
                                                                 unit=self.unit)
            if not data.isError():
                try:
                    value = await self.decode(value=data.registers, obj=obj)
                    obj.value = value
                except (TypeError, Exception) as e:
                    self._LOG.warning(f'Decode error: {e}')
                    obj.value = 'null'
                    obj.reliability = 'decode_error'
            else:
                self._LOG.error(f'Received error response from {reg_address}')
                obj.value = 'null'
                obj.reliability = '0x80_response'
        except asyncio.TimeoutError:
            self._LOG.warning('Read timeout',
                              extra={'register': reg_address, 'quantity': quantity})
            obj.value = 'null'
            obj.reliability = 'timeout'
        except ModbusException as e:
            obj.value = 'null'
            obj.reliability = str(e)
            self._LOG.warning('Read error',
                              extra={'register': reg_address,
                                     'quantity': quantity,
                                     'exception': str(e)})
        except Exception as e:
            self._LOG.critical(f'Unexpected error: {e}')
        finally:
            return obj.value

    async def write(self, value, obj: ModbusObjModel) -> None:
        """Write data to Modbus object."""
        try:
            write_cmd_code = obj.property_list.modbus.func_write
            if write_cmd_code not in self.write_funcs:
                raise ValueError(f'Read functions must be one of {self.write_funcs.keys()}')
            reg_address = obj.property_list.modbus.address

            # encoded_value = TODO encode here

            # Using lock because pymodbus doesn't handle async requests internally.
            # Maybe this will change in pymodbus v3.0.0
            async with self._lock:
                rq = await self.write_funcs[write_cmd_code.code](reg_address,
                                                                 value,
                                                                 unit=self.unit)
            if not rq.isError():
                self._LOG.debug(f'Successfully write: {reg_address}: {value}')
            else:
                self._LOG.warning(f'Failed write: {rq}')
                # raise rq  # fixme: isn't exception
        except Exception as e:
            self._LOG.exception(e)

    async def start_periodic_polls(self) -> None:
        """Starts periodic polls for all periods."""

        if self.is_client_connected:
            for period, objs in self._objects.items():
                await self.scheduler.spawn(self.periodic_poll(objs=objs, period=period))
            self._LOG.debug('Periodic polls started')
        else:
            self._LOG.info('pymodbus client is not connected. '
                           f'Sleeping {self.reconnect_period} sec before next try')
            await asyncio.sleep(delay=self.reconnect_period)
            await self._gateway.async_add_job(self.create_client)
            self._gateway.async_add_job(self.start_periodic_polls)

    async def periodic_poll(self, objs: Collection[ModbusObjModel], period: int) -> None:
        self._LOG.debug(f'Periodic poll task created for period {period}')
        await self.scheduler.spawn(self._poll_objects(objs=objs, period=period))
        # await self._poll_objects(objs=objs)
        await asyncio.sleep(delay=period)

        await self.scheduler.spawn(self.periodic_poll(objs=objs, period=period))
        # self._poll_tasks[period] = self._loop.create_task(
        #     self.periodic_poll(objs=objs, period=period))

    async def _poll_objects(self, objs: Collection[ModbusObjModel], period: int) -> None:
        """Polls objects and set new periodic job in period.

        Args:
            objs: Objects to poll
            period: Time to start new poll job.
        """
        read_tasks = [self.read(obj=obj) for obj in objs]
        self._LOG.debug('Perform reading')
        _t0 = datetime.now()
        # await self.scheduler.spawn(asyncio.gather(*read_tasks))
        await asyncio.gather(*read_tasks)
        _t_delta = datetime.now() - _t0
        if _t_delta.seconds > period:
            self._LOG.critical('POLL PERIOD IS TOO SHORT! Requests may interfere selves.')
            # TODO implement period increasing algorithm
        self._LOG.info('Objects polled', extra={'device_id': self.id,
                                                'poll_period': period,
                                                'time_spent': _t_delta.seconds,
                                                'objects_polled': len(objs)
                                                })
        await self._gateway.verify_objects(objs=objs)
        await self._gateway.send_objects(objs=objs)

    # async def start_poll(self):
    #     self._log.info(f'{self} started')
    #     while self._polling:
    #         if hasattr(self._client, 'protocol') and self._client.protocol is not None:
    #             _t0 = time()
    #             # todo kill running tasks at updating
    #             done, pending = await asyncio.wait({self.poll(objects=self.objects)},
    #                                                loop=self._loop)
    #             # self._loop.run_until_complete(self.poll(objects=self.objects))
    #             _t_delta = time() - _t0
    #             self._log.info(
    #                 '\n==================================================\n'
    #                 f'{self} ip:{self.address} polled for: '
    #                 f'{round(_t_delta, ndigits=1)} sec.\n'
    #                 f'Update period: {self.upd_period} sec.\n'
    #                 f'Objects: {len(self)}\n'
    #             )
    #             if _t_delta < self.upd_period:
    #                 _delay = (self.upd_period - _t_delta) * self.upd_period_factor
    #                 self._log.debug(f'Sleeping {round(_delay, ndigits=1)} sec ...')
    #                 await asyncio.sleep(_delay)
    #         else:
    #             self._log.debug('Connecting to client ...')
    #             try:
    #                 self._loop, self._client = self._get_client(host=self.address,
    #                                                             port=self.port)
    #                 self.read_funcs, self.write_funcs = self._get_functions(
    #                     client=self._client)
    #             except ConnectionError as e:
    #                 self._log.warning(
    #                     f'{self} connection error: {e} '
    #                     f'Wait {self.delay_next_attempt} sec. before next attempt ...')
    #                 await asyncio.sleep(self.delay_next_attempt)
    #             except Exception as e:
    #                 self._log.exception(e, exc_info=True)
    #     else:
    #         self._log.info(f'{self} stopped')

    # def _put_device_end_to_verifier(self) -> None:
    #     """device_id in queue means that device polled.
    #     Should send collected objects to HTTP
    #     """
    #     self._verifier_queue.put(self.id)

    async def decode(self, value: list[int], obj: ModbusObjModel) -> Union[float, int]:
        return await self._gateway.add_job(self._decode_register, value, obj)

    def _decode_register(self, value: list[int], obj: ModbusObjModel) -> Union[float, int]:
        data_length = obj.property_list.modbus.data_length
        data_type = obj.property_list.modbus.data_type.lower()

        reg_address = obj.property_list.modbus.address
        quantity = obj.property_list.modbus.quantity

        scale = obj.property_list.modbus.scale
        offset = obj.property_list.modbus.offset

        # todo process in parse
        byte_order = Endian.Big if obj.property_list.modbus.byte_order == 'big' else Endian.Little
        word_order = Endian.Big if obj.property_list.modbus.word_order == 'big' else Endian.Little
        # repack = obj.property_list.modbus.repack

        decoder = BinaryPayloadDecoder(payload=value, byteorder=byte_order,
                                       wordorder=word_order)

        decode_funcs = {
            'bits': decoder.decode_bits,
            'bool': None,  # todo
            'string': decoder.decode_string,
            8: {'int': decoder.decode_8bit_int,
                'uint': decoder.decode_8bit_uint, },
            16: {'int': decoder.decode_16bit_int,
                 'uint': decoder.decode_16bit_uint,
                 'float': decoder.decode_16bit_float, },
            32: {'int': decoder.decode_32bit_int,
                 'uint': decoder.decode_32bit_uint,
                 'float': decoder.decode_32bit_float, },
            64: {'int': decoder.decode_64bit_int,
                 'uint': decoder.decode_64bit_uint,
                 'float': decoder.decode_64bit_float, }
        }
        assert decode_funcs[data_length][data_type] is not None
        decoded = decode_funcs[data_length][data_type]()
        decoded_value = decoded * scale + offset
        self._LOG.debug(f'Decoded {reg_address}({quantity})= {value} -> '
                        f'{data_length}{data_type}= {decoded} -> '
                        f'*{scale} +{offset} -> {decoded_value}')
        return decoded_value

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

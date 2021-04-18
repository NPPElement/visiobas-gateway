import asyncio
from logging import getLogger
from typing import Any, Optional, Callable, Union, Collection

from pymodbus.client.asynchronous.schedulers import ASYNC_IO
from pymodbus.client.asynchronous.serial import AsyncModbusSerialClient
from pymodbus.client.asynchronous.tcp import AsyncModbusTCPClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder

from gateway.models import BACnetDeviceModel, ModbusObjModel, ObjType

# aliases
# BACnetDeviceModel = Any  # ...models
VisioBASGateway = Any  # ...gateway_loop


class AsyncModbusDevice:
    upd_period_factor = 0.9  # todo provide from config
    delay_next_attempt = 60  # todo provide from config

    def __init__(self, device_obj: BACnetDeviceModel,  # 'BACnetDeviceModel'
                 gateway: 'VisioBASGateway'):
        self._gateway = gateway
        self._device_obj = device_obj

        self._log = getLogger(name=f'{self.id}')

        self._loop, self._client = None, None

        self._polling = True
        self._objects: Collection[ModbusObjModel] = []  # 'BACnetObjModel'
        # todo switch do dict

    @property
    def types_to_rq(self) -> tuple[ObjType, ...]:  # todo hide type
        return self._device_obj.types_to_rq

    @property
    def id(self) -> int:
        return self._device_obj.id

    @property
    def address(self) -> Optional[tuple[str, int]]:  # todo switch to IP object
        address = self._device_obj.address
        if isinstance(address, str):
            host, port = self._device_obj.address.split(sep=':', maxsplit=1)
            return host, int(port)

    @property
    def unit(self) -> int:
        unit = self._device_obj.address
        if isinstance(unit, int) and not isinstance(unit, bool):
            return unit
        else:
            return 0x01

    @property
    def protocol(self) -> str:
        return self._device_obj.protocol

    @property
    def timeout(self) -> float:
        return self._device_obj.timeout

    @property
    def retries(self) -> int:
        return self._device_obj.retries

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}[{self.id}]'

    def __len__(self) -> int:
        return len(self._objects)

    @property
    def is_client_initialized(self) -> bool:
        if hasattr(self._client, 'protocol') and self._client.protocol is not None:
            return True
        return False

    async def init_client(self) -> None:
        setup_task = self._gateway.add_job(self._init_client)

    def _init_client(self) -> None:
        """Initializes asynchronously modbus client.

        Raises:
            ConnectionError: if client is not initialized.
        """
        if self.protocol == 'ModbusTCP':
            host, port = self.address
            loop, self._client = AsyncModbusTCPClient(
                scheduler=ASYNC_IO,
                host=host, port=port,
                retries=self.retries,
                retry_on_empty=True,
                retry_on_invalid=True,
                loop=self._gateway.loop,
                timeout=self.timeout
            )
        elif self.protocol == 'ModbusRTU':
            loop, self._client = AsyncModbusSerialClient(
                scheduler=ASYNC_IO,
                method='rtu',
                port=self._device_obj.property_list.rtu.port,
                baudrate=self._device_obj.property_list.rtu.baudrate,
                bytesize=self._device_obj.property_list.rtu.bytesize,
                parity=self._device_obj.property_list.rtu.parity,
                stopbits=self._device_obj.property_list.rtu.stopbits,
                retries=self.retries,
                retry_on_empty=True,
                retry_on_invalid=True,
                loop=self._gateway.loop,
                timeout=self.timeout
            )
        else:
            raise NotImplementedError('Other methods not support yet.')

        if self.is_client_initialized:
            self._log.debug(f'Connected to {self}')
        else:
            raise ConnectionError(f'Failed to connect to {self}({self.address})')

    def load_objects(self, objs: Collection[ModbusObjModel]) -> None:
        """Loads object to poll.
        Group by poll period.
        """
        self._objects = objs
        # todo

    async def start_poll(self):
        pass

    @property
    def read_funcs(self) -> dict[int, Callable]:
        if not self.is_client_initialized:
            raise ConnectionError('Ensure client connected')
        read_funcs = {1: self._client.protocol.read_coils,
                      2: self._client.protocol.read_discrete_inputs,
                      3: self._client.protocol.read_holding_registers,
                      4: self._client.protocol.read_input_registers, }
        return read_funcs

    @property
    def write_funcs(self) -> dict[int, Callable]:
        if not self.is_client_initialized:
            raise ConnectionError('Ensure client connected')
        write_funcs = {5: self._client.protocol.write_coil,
                       6: self._client.protocol.write_register,
                       15: self._client.protocol.write_coils,
                       16: self._client.protocol.write_registers, }
        return write_funcs

    async def read(self, obj: ModbusObjModel) -> Union[float, int, str]:
        """Read data from Modbus object."""
        # todo: set reliability in fail cases

        read_cmd_code = obj.property_list.modbus.func_read
        reg_address = obj.property_list.modbus.address
        quantity = obj.property_list.modbus.quantity

        if read_cmd_code not in self.read_funcs:
            raise ValueError(f'Read functions must be one from {self.read_funcs.keys()}')
        try:
            data = await self.read_funcs[read_cmd_code.code](address=reg_address,
                                                             count=quantity,
                                                             unit=self.unit)
            if not data.isError():
                try:
                    value = await self.decode(value=data.registers, obj=obj)
                    return value
                except TypeError as e:
                    self._log.warning(f'Decode error: {e}')
                    return 'null'
            else:
                self._log.error(f'Received error response from {reg_address}')
                return 'null'
        except asyncio.TimeoutError as e:
            self._log.error(f'reg: {reg_address} quantity: {quantity} '
                            f'Read Timeout: {e}')
            return 'null'
        except Exception as e:
            self._log.error(
                f'Read error from reg: {reg_address}, quantity: {quantity} : {e}')

    async def write(self, value, obj: ModbusObjModel) -> None:
        """Write data to Modbus object."""
        try:
            write_cmd_code = obj.property_list.modbus.func_write
            if write_cmd_code not in self.write_funcs:
                raise ValueError(f'Read functions must be one of {self.write_funcs.keys()}')
            reg_address = obj.property_list.modbus.address

            # encoded_value = TODO encode here

            rq = await self.write_funcs[write_cmd_code.code](reg_address,
                                                             value,
                                                             unit=self.unit)
            if not rq.isError():
                self._log.debug(f'Successfully write: {reg_address}: {value}')
            else:
                self._log.warning(f'Failed write: {rq}')
                # raise rq  # fixme: isn't exception
        except Exception as e:
            self._log.exception(e)

    # async def poll(self, objects: Sequence[ModbusObjModel]) -> None:
    #     """Represent one iteration of poll."""
    #     read_requests = [self.read_send_to_verifier(obj=obj,
    #                                                 queue=self._verifier_queue
    #                                                 ) for obj in objects]
    #     await asyncio.gather(*read_requests)
    #     self._put_device_end_to_verifier()

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
        self._log.debug(f'Decoded {reg_address}({quantity})= {value} -> '
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

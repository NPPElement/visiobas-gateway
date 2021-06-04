import asyncio
from abc import abstractmethod, ABC
from datetime import datetime
from functools import lru_cache
from ipaddress import IPv4Address
from typing import Any, Callable, Union, Collection, Optional

import aiojobs
from pymodbus.bit_read_message import (ReadCoilsResponse, ReadDiscreteInputsResponse,
                                       ReadBitsResponseBase)
from pymodbus.client.asynchronous.async_io import (AsyncioModbusSerialClient,
                                                   AsyncioModbusTcpClient)
from pymodbus.client.sync import ModbusSerialClient
from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder
from pymodbus.register_read_message import (ReadHoldingRegistersResponse,
                                            ReadInputRegistersResponse,
                                            ReadRegistersResponseBase)

from ..models import (BACnetDevice, BACnetObj, ModbusObj, ObjType, Protocol, DataType,
                      ModbusReadFunc, ModbusWriteFunc)
from ..utils import get_file_logger

# aliases # TODO
# BACnetDeviceModel = Any  # ...models


VisioBASGateway = Any  # ...gateway_loop


# _LOG = get_file_logger(name=__name__, size_mb=500)


class BaseModbusDevice(ABC):
    # upd_period_factor = 0.9  # todo provide from config

    # Keys is serial port names.
    _serial_clients: dict[str: Union[ModbusSerialClient,
                                     AsyncioModbusSerialClient]] = {}
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

        # self._loop: asyncio.AbstractEventLoop = None
        self._client = None
        self.scheduler: aiojobs.Scheduler = None

        # self._lock = asyncio.Lock()

        self._polling = True
        self._objects: dict[int, set[ModbusObj]] = {}  # todo hide type

        self._connected = False

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}[{self.id}]'

    def __len__(self) -> int:
        return len(self._objects)

    @classmethod
    async def create(cls, device_obj: BACnetDevice, gateway: 'VisioBASGateway'
                     ) -> 'BaseModbusDevice':
        dev = cls(device_obj=device_obj, gateway=gateway)
        dev.scheduler = await aiojobs.create_scheduler(close_timeout=60, limit=100)
        await dev._gateway.async_add_job(dev.create_client)
        # _LOG.debug('Device created', extra={'device_id': dev.id})
        return dev

    # @property
    # def lock(self) -> asyncio.Lock:
    #     return self._serial_locks.get(self.serial_port) or self._lock

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
        return 3  # self._device_obj.timeout_sec

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
    def objects(self) -> set[ModbusObj]:
        return {obj for objs_set in self._objects.values() for obj in objs_set}

    @abstractmethod
    def read_funcs(self) -> dict[ModbusReadFunc, Callable]:
        raise NotImplementedError

    @abstractmethod
    def write_funcs(self) -> dict[ModbusWriteFunc, Callable]:
        raise NotImplementedError

    @abstractmethod
    def create_client(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def is_client_connected(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def _poll_objects(self, objs: Collection[ModbusObj]) -> None:
        raise NotImplementedError

    @lru_cache(maxsize=10)
    def get_object(self, obj_id: int, obj_type_id: int) -> Optional[ModbusObj]:
        """Cache last 10 object instances.
        Args:
            obj_id: Object identifier.
            obj_type_id: Object type identifier.

        Returns:
            Object instance.
        """
        for obj in self.objects:
            if obj.type.id == obj_type_id and obj.id == obj_id:
                return obj

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
        # todo: add close event wait

    async def periodic_poll(self, objs: set[ModbusObj], period: int) -> None:
        await self.scheduler.spawn(self._poll_iter(objs=objs, period=period))
        self._LOG.debug(f'Periodic polling task created',
                        extra={'device_id': self.id, 'period': period,
                               'jobs_active_count': self.scheduler.active_count,
                               'jobs_pending_count': self.scheduler.pending_count, })
        # await self._poll_objects(objs=objs)
        await asyncio.sleep(delay=period)

        # Period of poll may change in the polling
        await self.scheduler.spawn(self.periodic_poll(objs=objs, period=period))

    async def _poll_iter(self, objs: Collection[ModbusObj], period: int) -> None:
        """Polls objects and set new periodic job in period.

        Args:
            objs: Objects to poll
            period: Time to start new poll job.
        """
        self._LOG.debug('Polling started',
                        extra={'device_id': self.id, 'period': period,
                               'objects_polled': len(objs)})
        _t0 = datetime.now()
        await self._poll_objects(objs=objs)
        _t_delta = datetime.now() - _t0
        if _t_delta.seconds > period:
            # TODO: improve tactic
            self._LOG.warning('Polling period is too short! ',
                              extra={'device_id': self.id, })

        self._LOG.info('Objects polled',
                       extra={'device_id': self.id, 'period': period,
                              'seconds_took': _t_delta.seconds,
                              'objects_polled': len(objs)})
        await self._gateway.verify_objects(objs=objs)
        await self._gateway.send_objects(objs=objs)
        await self._gateway.async_add_job(self.clear_properties, objs)  # fixme hotfix

    @staticmethod
    def clear_properties(objs: Collection[BACnetObj]) -> None:
        [obj.clear_properties() for obj in objs]  # fixme hotfix

    def _decode_response(self, resp: Union[ReadCoilsResponse,
                                           ReadDiscreteInputsResponse,
                                           ReadHoldingRegistersResponse,
                                           ReadInputRegistersResponse],
                         obj: ModbusObj) -> Union[bool, int, float]:
        """Decodes value from registers and scale them.
        # TODO make 4 decoders for all combinations in bo, wo and use them?
        Args:
            resp: Read request response.
            obj: Object instance

        Returns:
            Decoded from register\bits and scaled value.
        """

        # TODO: Add decode with different byteorder in bytes VisioDecoder class

        if isinstance(resp, ReadBitsResponseBase):
            data = resp.bits
            return 1 if data[0] else 0  # TODO: add support several bits?
        elif isinstance(resp, ReadRegistersResponseBase):
            data = resp.registers

            if obj.data_type == DataType.BOOL:
                if obj.data_length == 1:
                    scaled = decoded = 1 if data[0] else 0
                elif obj.bit:
                    scaled = decoded = 1 if data[obj.bit] else 0
                else:
                    scaled = decoded = any(data)
            else:
                decoder = BinaryPayloadDecoder.fromRegisters(
                    registers=data, byteorder=obj.byte_order,
                    wordorder=obj.word_order)
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
                assert decode_funcs[obj.data_length][obj.data_type] is not None

                decoded = decode_funcs[obj.data_length][obj.data_type]()
                scaled = decoded * obj.scale + obj.offset  # Scaling
            self._LOG.debug('Decoded',
                            extra={'device_id': obj.device_id, 'object_id': obj.id,
                                   'object_type': obj.type,
                                   'register_address': obj.address,
                                   'quantity': obj.quantity, 'data_length': obj.data_length,
                                   'data_type': obj.data_type, 'value_raw': data,
                                   'value_decoded': decoded, 'value_scaled': scaled})
            return scaled

    def _build_payload(self, value: Union[int, float], obj: ModbusObj
                       ) -> Union[int, list[Union[int, bytes, bool]]]:
        """
        # TODO make 4 decoders for all combinations in bo, wo and use them?
        Args:
            value: Value to write in object.
            obj: Object instance.

        Returns:
            Built payload.
        """
        scaled = int(value / obj.scale - obj.offset)  # Scaling

        # In `pymodbus` example INT and UINT values presented by hex values.
        # value = hex(value) if obj.data_type in {DataType.INT, DataType.UINT} else value

        if obj.data_type is DataType.BOOL and obj.data_length in {1, 16}:
            # scaled = [scaled] + [0] * 7
            return int(bool(scaled))

        builder = BinaryPayloadBuilder(byteorder=obj.byte_order, wordorder=obj.word_order,
                                       repack=True)
        build_funcs = {
            # 1: {DataType.BOOL: builder.add_bits},
            8: {DataType.INT: builder.add_8bit_int,
                DataType.UINT: builder.add_8bit_uint,
                # DataType.BOOL: builder.add_bits,
                },
            16: {DataType.INT: builder.add_16bit_int,
                 DataType.UINT: builder.add_16bit_uint,
                 DataType.FLOAT: builder.add_16bit_float,
                 # DataType.BOOL: builder.add_bits,
                 },
            32: {DataType.INT: builder.add_32bit_int,
                 DataType.UINT: builder.add_32bit_uint,
                 DataType.FLOAT: builder.add_32bit_float, },
            64: {DataType.INT: builder.add_64bit_int,
                 DataType.UINT: builder.add_64bit_uint,
                 DataType.FLOAT: builder.add_64bit_float, },
        }
        assert build_funcs[obj.data_length][obj.data_type] is not None

        build_funcs[obj.data_length][obj.data_type](scaled)

        # FIXME: string not support now
        payload = builder.to_coils() if obj.is_coil else builder.to_registers()

        # payload = builder.build()
        self._LOG.debug('Encoded',
                        extra={'device_id': obj.device_id, 'object_id': obj.id,
                               'object_type': obj.type,
                               'object_is_register': obj.is_register,
                               'objects_is_coil': obj.is_coil,
                               'register_address': obj.address,
                               'quantity': obj.quantity, 'data_length': obj.data_length,
                               'data_type': obj.data_type, 'value_raw': value,
                               'value_scaled': scaled, 'value_encoded': payload, })
        return payload

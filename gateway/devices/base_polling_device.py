import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from functools import lru_cache
from typing import Any, Optional, Collection, Union

import aiojobs
from pymodbus.client.asynchronous.async_io import AsyncioModbusSerialClient
from pymodbus.client.sync import ModbusSerialClient

from ..models import (BACnetDeviceObj, BACnetObj, ModbusObj, ObjType, Protocol)
from .base_device import BaseDevice

# Aliases
VisioBASGateway = Any  # ...gateway_


class BasePollingDevice(BaseDevice, ABC):
    # TODO: implement Singleton by device_id

    _client_creation_lock: asyncio.Lock = None

    # Key is serial port name.
    _serial_clients: dict[str: Union[ModbusSerialClient,
                                     AsyncioModbusSerialClient]] = {}
    _serial_port_locks: dict[str: asyncio.Lock] = {}
    _serial_polling: dict[str: asyncio.Event] = {}
    _serial_connected: dict[str, bool] = {}

    def __init__(self, device_obj: BACnetDeviceObj, gateway: 'VisioBASGateway'):
        super().__init__(device_obj, gateway)

        self._scheduler: aiojobs.Scheduler = None

        # Key: period
        self._objects: dict[int, set[Union[BACnetObj, ModbusObj]]] = {}
        self._unreachable_objects: set[Union[BACnetObj, ModbusObj]] = set()
        # self._nonexistent_objects: set[Union[BACnetObj, ModbusObj]] = set()

        self._connected = False

        # IMPORTANT: clear that event to change the objects (load or priority write).
        # Wait that event in polling to provide priority access to write_with_check.
        self._polling = asyncio.Event()

    @property
    def is_client_connected(self) -> bool:
        return bool(
            self._serial_connected.get(self.serial_port)) if self.protocol is Protocol.MODBUS_RTU else self._connected

    @classmethod
    async def create(cls, device_obj: BACnetDeviceObj, gateway) -> 'BasePollingDevice':
        loop = gateway.loop
        if cls._client_creation_lock is None:
            cls._client_creation_lock = asyncio.Lock(loop=loop)

        dev = cls(device_obj=device_obj, gateway=gateway)
        dev._scheduler = await aiojobs.create_scheduler(close_timeout=60, limit=100)
        async with cls._client_creation_lock:
            await dev._gtw.async_add_job(dev.create_client)
        dev._LOG.debug('Device created',
                       extra={'device_id': dev.id, 'protocol': dev.protocol,
                              'serial_clients_dict': cls._serial_clients, })
        return dev

    @property
    def serial_port(self) -> Optional[str]:
        """
        Returns:
            Serial port name if exists. Else None.
        """
        if self.protocol is Protocol.MODBUS_RTU:
            return self._dev_obj.property_list.rtu.port

    @property
    def _polling_event(self) -> asyncio.Event:
        return self._serial_polling[self.serial_port] if self.protocol is Protocol.MODBUS_RTU else self._polling

    @property
    def types_to_rq(self) -> tuple[ObjType, ...]:
        return self._dev_obj.types_to_rq

    @property
    def reconnect_period(self) -> int:
        return self._dev_obj.property_list.reconnect_period

    @property
    def retries(self) -> int:
        return self._dev_obj.retries

    @property
    def all_objects(self) -> set[Union[BACnetObj, ModbusObj]]:
        return {obj for objs_set in self._objects.values() for obj in objs_set}

    # @abstractmethod
    # def is_client_connected(self) -> bool:
    #     raise NotImplementedError

    @abstractmethod
    def create_client(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def close_client(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def _poll_objects(self, objs: Collection[Union[BACnetObj, ModbusObj]]) -> None:
        raise NotImplementedError

    @abstractmethod
    async def read(self, obj: BACnetObj, **kwargs) -> Optional[Union[int, float, str]]:
        raise NotImplementedError(
            'You should implement async read method for your device'
        )

    @abstractmethod
    async def write(self, value: Union[int, float], obj: BACnetObj, **kwargs) -> None:
        raise NotImplementedError(
            'You should implement async write method for your device'
        )

    async def write_with_check(self, value: Union[int, float], obj: BACnetObj,
                               **kwargs) -> bool:
        """Writes value to object at controller and check it by read.

        Args:
            value: Value to write.
            obj: Objects instance.
            **kwargs:

        Returns:
            True - if write value and read value is consistent.
            False - if they aren't consistent.
        """
        self._polling_event.clear()
        await self.write(value=value, obj=obj, **kwargs)
        read_value = await self.read(obj=obj, wait=False, **kwargs)
        self._polling_event.set()

        is_consistent = value == read_value
        self._LOG.debug('Write with check called',
                        extra={'device_id': obj.device_id, 'object_id': obj.id,
                               'object_type': obj.type, 'value_written': value,
                               'value_read': read_value,
                               'values_are_consistent': is_consistent, })
        return is_consistent

    @lru_cache(maxsize=10)
    def get_object(self, obj_id: int, obj_type_id: int
                   ) -> Optional[Union[BACnetObj, ModbusObj]]:
        """Cache last 10 object instances.
        Args:
            obj_id: Object identifier.
            obj_type_id: Object type identifier.

        Returns:
            Object instance.
        """
        for obj in self.all_objects:
            if obj.type.id == obj_type_id and obj.id == obj_id:
                return obj

    def load_objects(self, objs: Collection[Union[BACnetObj, ModbusObj]]) -> None:
        """Groups objects by poll period and loads them into device for polling."""
        if not len(objs):
            self._LOG.debug('No objects to load', extra={'device_id': self.id, })
            return None

        self._polling_event.clear()
        for obj in objs:
            poll_period = obj.property_list.send_interval
            try:
                self._objects[poll_period].add(obj)
            except KeyError:
                self._objects[poll_period] = {obj}
        self._polling_event.set()
        self._LOG.debug('Objects are grouped by period and loads to the device',
                        extra={'device_id': self.id, 'objects_number': len(objs)})

    async def start_periodic_pollings(self) -> None:
        """Starts periodic pollings for all periods."""

        if self.is_client_connected:
            self._polling_event.set()
            for period, objs in self._objects.items():
                await self._scheduler.spawn(self.periodic_poll(objs=objs, period=period, first_iter=True))
            await self._scheduler.spawn(self._periodic_reset_unreachable())
        else:
            self._LOG.info('Client is not connected. Sleeping to next try',
                           extra={'device_id': self.id,
                                  'seconds_to_next_try': self.reconnect_period, })
            await asyncio.sleep(delay=self.reconnect_period)
            await self._gtw.async_add_job(self.create_client)
            await self._scheduler.spawn(self.start_periodic_pollings())

    async def stop(self) -> None:
        """Waits for finish of all polling tasks with timeout, and stop polling.
        Closes client.
        """
        self._LOG.debug('stop call')
        self._polling_event.clear()
        await self._scheduler.close()
        self._LOG.debug('scheduler closed')
        self.close_client()  # todo: left client open if used by another device
        self._LOG.info('Device stopped', extra={'device_id': self.id, })

    async def _periodic_reset_unreachable(self) -> None:
        await asyncio.sleep(self._gtw.unreachable_reset_period)

        self._LOG.debug('Reset unreachable objects',
                        extra={'device_id': self.id,
                               'unreachable_objects_number': len(self._unreachable_objects)})
        self.load_objects(objs=self._unreachable_objects)
        self._unreachable_objects = set()

        await self._scheduler.spawn(self._periodic_reset_unreachable())

    async def periodic_poll(self, objs: set[Union[BACnetObj, ModbusObj]],
                            period: int, *, first_iter: bool = False) -> None:
        self._LOG.debug('Polling started',
                        extra={'device_id': self.id, 'period': period,
                               'objects_number': len(objs)})
        _t0 = datetime.now()
        await self._poll_objects(objs=objs)
        self._check_unreachable(objs=objs, period=period)  # hotfix
        if first_iter:
            nonexistent_objs = {obj for obj in objs if not obj.existing}
            objs -= nonexistent_objs
            self._LOG.info('Removed non-existent objects',
                           extra={'device_id': self.id, 'nonexistent_objects': nonexistent_objs,
                                  'nonexistent_objects_number': len(nonexistent_objs)})

        _t_delta = datetime.now() - _t0
        self._LOG.info('Objects polled',
                       extra={'device_id': self.id, 'seconds_took': _t_delta.seconds,
                              'objects_number': len(objs), 'period': period, })

        if _t_delta.seconds > period:
            # period *= 1.5
            self._LOG.warning('Polling period is too short!',
                              extra={'device_id': self.id})
        await self._scheduler.spawn(self._process_polled(objs=objs))
        await asyncio.sleep(delay=period - _t_delta.seconds)

        # self._LOG.debug(f'Periodic polling task created',
        #                 extra={'device_id': self.id, 'period': period,
        #                        'jobs_active_count': self.scheduler.active_count,
        #                        'jobs_pending_count': self.scheduler.pending_count, })

        await self._scheduler.spawn(self.periodic_poll(objs=objs, period=period))

    async def _process_polled(self, objs: set[Union[BACnetObj, ModbusObj]]) -> None:
        await self._gtw.verify_objects(objs=objs)
        await self._gtw.send_objects(objs=objs)

    def _check_unreachable(self, objs: set[Union[BACnetObj, ModbusObj]], period: int
                           ) -> None:
        for obj in objs.copy():
            if obj.unreachable_in_row >= self._gtw.unreachable_threshold:
                self._LOG.debug('Marked as unreachable',
                                extra={'device_id': obj.device_id,
                                       'object_id': obj.id, 'object_type': obj.type, })
                self._objects[period].remove(obj)
                self._unreachable_objects.add(obj)

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from functools import lru_cache
from ipaddress import IPv4Address
from typing import Any, Optional, Collection, Union

import aiojobs
from pymodbus.client.asynchronous.async_io import AsyncioModbusSerialClient
from pymodbus.client.sync import ModbusSerialClient

from ..models import (BACnetDeviceObj, BACnetObj, ModbusObj, ObjType, Protocol)
from ..utils import get_file_logger

# Aliases
VisioBASGateway = Any  # ...gateway_


class BaseDevice(ABC):
    # TODO: implement Singleton by device_id

    _client_creation_lock: asyncio.Lock = None

    # Keys is serial port names.
    _serial_clients: dict[str: Union[ModbusSerialClient,
                                     AsyncioModbusSerialClient]] = {}
    _serial_port_locks: dict[str: asyncio.Lock] = {}

    def __init__(self, device_obj: BACnetDeviceObj, gateway: 'VisioBASGateway'):
        self._gateway = gateway
        self._device_obj = device_obj
        self._LOG = get_file_logger(name=__name__ + str(self.id))

        self.scheduler: aiojobs.Scheduler = None

        # Key: period
        self._objects: dict[int, set[Union[BACnetObj, ModbusObj]]] = {}
        self._unreachable_objects: set[Union[BACnetObj, ModbusObj]] = set()
        # todo: add check by period

        self._connected = False

    @classmethod
    async def create(cls, device_obj: BACnetDeviceObj, gateway: 'VisioBASGateway'
                     ) -> 'BaseDevice':
        loop = gateway.loop
        if cls._client_creation_lock is None:
            cls._client_creation_lock = asyncio.Lock(loop=loop)

        dev = cls(device_obj=device_obj, gateway=gateway)
        dev.scheduler = await aiojobs.create_scheduler(close_timeout=60, limit=100)
        async with cls._client_creation_lock:
            await dev._gateway.async_add_job(dev.create_client)
        dev._LOG.debug('Device created',
                       extra={'device_id': dev.id, 'protocol': dev.protocol,
                              'serial_clients_dict': cls._serial_clients, })
        return dev

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}[{self.id}]'

    def __len__(self) -> int:
        return len(self._objects)

    @property
    def id(self) -> int:
        """Device id."""
        return self._device_obj.id

    @property
    def address(self) -> Optional[IPv4Address]:
        return self._device_obj.property_list.address

    @property
    def port(self) -> Optional[int]:
        return self._device_obj.property_list.port

    @property
    def types_to_rq(self) -> tuple[ObjType, ...]:
        return self._device_obj.types_to_rq

    @property
    def protocol(self) -> Protocol:
        return self._device_obj.property_list.protocol

    @property
    def timeout(self) -> float:
        return self._device_obj.timeout_sec

    @property
    def reconnect_period(self) -> int:
        return self._device_obj.property_list.reconnect_period

    @property
    def retries(self) -> int:
        return self._device_obj.retries

    @property
    def all_objects(self) -> set[Union[BACnetObj, ModbusObj]]:
        return {obj for objs_set in self._objects.values() for obj in objs_set}

    @abstractmethod
    def is_client_connected(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def create_client(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def close_client(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def _poll_objects(self, objs: Collection[Union[BACnetObj, ModbusObj]]) -> None:
        raise NotImplementedError

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
        assert len(objs)

        for obj in objs:
            poll_period = obj.property_list.send_interval
            try:
                self._objects[poll_period].add(obj)
            except KeyError:
                self._objects[poll_period] = {obj}
        self._LOG.debug('Objects are grouped by period and loads to the device',
                        extra={'device_id': self.id, 'objects_number': len(objs)})

    async def start_periodic_polls(self) -> None:
        """Starts periodic polls for all periods."""

        if self.is_client_connected:
            for period, objs in self._objects.items():
                await self.scheduler.spawn(self.periodic_poll(objs=objs, period=period))
                # self._LOG.debug('Periodic polling started',
                #            extra={'device_id': self.id, 'period': period})
        else:
            self._LOG.info('Client is not connected. Sleeping to next try',
                           extra={'device_id': self.id,
                                  'seconds_to_next_try': self.reconnect_period})
            await asyncio.sleep(delay=self.reconnect_period)
            await self._gateway.async_add_job(self.create_client)
            # self._gateway.async_add_job(self.start_periodic_polls)
            await self.scheduler.spawn(self.start_periodic_polls())
            await self.scheduler.spawn(self._periodic_reset_unreachable())

        # todo: add close event wait

    async def stop(self) -> None:
        """Waits for finish of all polling tasks with timeout, and stop polling.
        Closes client.
        """
        await self.scheduler.close()
        self._LOG.info('Device stopped', extra={'device_id': self.id})

    async def _periodic_reset_unreachable(self) -> None:
        await asyncio.sleep(self._gateway.unreachable_check_period)

        self._LOG.debug('Reset unreachable objects')
        self.load_objects(objs=self._unreachable_objects)
        self._unreachable_objects = set()

        await self.scheduler.spawn(self._periodic_reset_unreachable())

    async def periodic_poll(self, objs: set[Union[BACnetObj, ModbusObj]],
                            period: int) -> None:
        self._LOG.debug('Polling started',
                        extra={'device_id': self.id, 'period': period,
                               'objects_polled': len(objs)})
        _t0 = datetime.now()
        await self._poll_objects(objs=objs)
        _t_delta = datetime.now() - _t0
        self._LOG.info('Objects polled',
                       extra={'device_id': self.id, 'seconds_took': _t_delta.seconds,
                              'objects_polled': len(objs), 'period': period, })

        if _t_delta.seconds > period:
            period *= 1.5
            self._LOG.warning('Polling period is too short! Increased in x1.5',
                              extra={'device_id': self.id})
        await self.scheduler.spawn(self._process_polled(objs=objs))
        await asyncio.sleep(delay=period - _t_delta.seconds)

        # self._LOG.debug(f'Periodic polling task created',
        #                 extra={'device_id': self.id, 'period': period,
        #                        'jobs_active_count': self.scheduler.active_count,
        #                        'jobs_pending_count': self.scheduler.pending_count, })
        # await asyncio.sleep(delay=period)

        # Period of poll may change in the polling
        await self.scheduler.spawn(self.periodic_poll(objs=objs, period=period))

    async def _process_polled(self, objs: set[Union[BACnetObj, ModbusObj]]):
        await self._gateway.verify_objects(objs=objs)
        await self._gateway.send_objects(objs=objs)
        # await self._gateway.async_add_job(self._clear_properties, objs)  # fixme hotfix

        for period, objs in self._objects.items():
            for obj in objs:
                if obj.unreachable_in_row >= self._gateway.unreachable_threshold:
                    self._objects[period].remove(obj)
                    self._unreachable_objects.add(obj)

    # async def _poll_iter(self, objs: Collection[Union[BACnetObj, ModbusObj]],
    #                      period: int) -> None:
    #     """Polls objects and set new periodic job in period.
    #
    #     Args:
    #         objs: Objects to poll
    #         period: Time to start new poll job.
    #     """
    #     self._LOG.debug('Polling started',
    #                     extra={'device_id': self.id, 'period': period,
    #                            'objects_polled': len(objs)})
    #     _t0 = datetime.now()
    #     await self._poll_objects(objs=objs)
    #     _t_delta = datetime.now() - _t0
    #     if _t_delta.seconds > period:
    #         # TODO: improve tactic
    #         self._LOG.warning('Polling period is too short! ',
    #                           extra={'device_id': self.id, })
    #
    #     self._LOG.info('Objects polled',
    #                    extra={'device_id': self.id, 'period': period,
    #                           'seconds_took': _t_delta.seconds,
    #                           'objects_polled': len(objs)})
    #     await self._gateway.verify_objects(objs=objs)
    #     await self._gateway.send_objects(objs=objs)
    #     await self._gateway.async_add_job(self._clear_properties, objs)  # fixme hotfix

    # @staticmethod
    # def _clear_properties(objs: Collection[Union[BACnetObj, ModbusObj]]) -> None:
    #     [obj.clear_properties() for obj in objs]  # fixme hotfix

    # @staticmethod
    # def _sort_objects_by_period(objs: Collection[Union[BACnetObj, ModbusObj]]
    #                             ) -> dict[int, set[Union[BACnetObj, ModbusObj]]]:
    #     """Creates dict from objects, where key is period, value is collection
    #     of objects with that period.
    #
    #     Returns:
    #         dict, where key is period, value is set of objects with that period.
    #     """
    #     dct = {}
    #
    #     return dct

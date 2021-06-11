import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from functools import lru_cache
from ipaddress import IPv4Address
from typing import Any, Optional, Collection, Union

import aiojobs

from ..models import (BACnetDeviceObj, BACnetObj, ModbusObj, ObjType, Protocol)
from ..utils import get_file_logger

# Aliases
VisioBASGateway = Any  # ...gateway_loop


class BaseDevice(ABC):
    # tODO: implement Singleton by device_id

    def __init__(self, device_obj: BACnetDeviceObj, gateway: 'VisioBASGateway'):
        self._gateway = gateway
        self._device_obj = device_obj
        self._LOG = get_file_logger(name=__name__ + str(self.id))

        self.scheduler: aiojobs.Scheduler = None

        self._polling = True
        self._objects: dict[int, set[Union[BACnetObj, ModbusObj]]] = {}  # todo hide type

        self._connected = False

    @classmethod
    async def create(cls, device_obj: BACnetDeviceObj, gateway: 'VisioBASGateway'
                     ) -> 'BaseDevice':
        dev = cls(device_obj=device_obj, gateway=gateway)
        dev.scheduler = await aiojobs.create_scheduler(close_timeout=60, limit=100)
        await dev._gateway.async_add_job(dev.create_client)
        # _LOG.debug('Device created', extra={'device_id': dev.id})
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
    def types_to_rq(self) -> tuple[ObjType, ...]:  # todo hide type
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
    def dev_obj(self) -> BACnetDeviceObj:
        return self._device_obj

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

        objs = self._sort_objects_by_period(objs=objs)
        self._objects = objs
        self._LOG.debug('Objects are grouped by period and loads to the device')

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
        # todo: add close event wait

    async def stop(self) -> None:
        """Waits for finish of all polling tasks with timeout, and stop polling.
        Closes client.
        """
        await self.scheduler.close()
        self._LOG.info('Device stopped', extra={'device_id': self.id})

    async def periodic_poll(self, objs: set[Union[BACnetObj, ModbusObj]],
                            period: int) -> None:
        self._LOG.debug('Polling started',
                        extra={'device_id': self.id, 'period': period,
                               'objects_polled': len(objs)})
        _t0 = datetime.now()
        await self._poll_objects(objs=objs)
        _t_delta = datetime.now() - _t0
        self._LOG.info('Objects polled',
                       extra={'device_id': self.id, 'period': period,
                              'seconds_took': _t_delta.seconds,
                              'objects_polled': len(objs)})

        if _t_delta.seconds > period:
            period *= 1.5
            self._LOG.warning('Polling period is too short! Increasing to x1.5',
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
        await self._gateway.async_add_job(self._clear_properties, objs)  # fixme hotfix

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

    @staticmethod
    def _clear_properties(objs: Collection[Union[BACnetObj, ModbusObj]]) -> None:
        [obj.clear_properties() for obj in objs]  # fixme hotfix

    @staticmethod
    def _sort_objects_by_period(objs: Collection[Union[BACnetObj, ModbusObj]]
                                ) -> dict[int, set[Union[BACnetObj, ModbusObj]]]:
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

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Collection, Optional, Union

import aiojobs  # type: ignore

from ..schemas import BACnetObj, DeviceObj
from ..utils.log import log_exceptions
from ._base_device import BaseDevice
from ._interface import Interface

if TYPE_CHECKING:
    from ..gateway import Gateway
else:
    Gateway = "Gateway"


class BasePollingDevice(BaseDevice, ABC):
    """Base class for devices, that can be periodically polled for update sensors data."""

    _interfaces: dict[str, Interface] = {}

    def __init__(self, device_obj: DeviceObj, gateway: Gateway):
        super().__init__(device_obj, gateway)

        self._scheduler: aiojobs.Scheduler = None  # type: ignore

        # Key: period
        self._objects: dict[float, set[BACnetObj]] = {}

    @staticmethod
    @abstractmethod
    def interface_name(device_obj: DeviceObj) -> Any:
        """Interface name, used to get access to interface."""

    @property
    def interface(self) -> Any:
        """Interface to interact with controller."""
        return self.__class__._interfaces.get(  # pylint: disable=protected-access
            self.interface_name(device_obj=self._device_obj)
        )

    @classmethod
    @log_exceptions
    async def create(cls, device_obj: DeviceObj, gateway: Gateway) -> BasePollingDevice:
        """Creates instance of device. Handles client creation with lock or using
        existing.
        """
        device = cls(device_obj=device_obj, gateway=gateway)
        device._scheduler = await aiojobs.create_scheduler(close_timeout=60, limit=100)

        interface_name = device.interface_name(device_obj=device_obj)

        if not cls._interfaces.get(interface_name):
            lock = asyncio.Lock(loop=gateway.loop)
            async with lock:  # pylint: disable=not-async-context-manager
                client = await device.create_client(device_obj=device_obj)
                client_connected = await device.connect_client(client=client)
            polling_event = asyncio.Event()
            interface = Interface(
                name=device.interface,
                used_by={device.id},
                client=client,
                lock=lock,
                polling_event=polling_event,
                client_connected=client_connected,
            )
            cls._interfaces[interface_name] = interface
        else:
            # Using existing interface.
            cls._interfaces[interface_name].used_by.add(device.id)

        device._LOG.debug(
            "Device created",
            extra={
                "device_id": device.id,
                "protocol": device.protocol,
                "device_interface": device.interface,
                "interface_state": cls._interfaces,
            },
        )
        return device

    @property
    def reconnect_period(self) -> int:
        return self._device_obj.property_list.reconnect_period

    @property
    def all_objects(self) -> set[BACnetObj]:
        return {obj for objs_set in self._objects.values() for obj in objs_set}

    @abstractmethod
    async def create_client(self, device_obj: DeviceObj) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def connect_client(self, client: Any) -> bool:
        raise NotImplementedError

    async def disconnect_client(self) -> None:
        if not self.interface.used_by:
            await self._disconnect_client(client=self.interface.client)

    @abstractmethod
    async def _disconnect_client(self, client: Any) -> None:
        raise NotImplementedError

    @property
    @abstractmethod
    def is_client_connected(self) -> bool:
        raise NotImplementedError

    async def _poll_objects(self, objs: Collection[BACnetObj]) -> None:
        for obj in objs:
            if not obj.existing:
                continue
            if obj.unreachable_in_row >= self._gtw.settings.unreachable_threshold:
                continue
            await self.read(obj=obj)

    @abstractmethod
    async def read(
        self, obj: BACnetObj, wait: bool = False, **kwargs: Any
    ) -> Optional[Union[int, float, str]]:
        """You should implement async read method for your device."""

    @abstractmethod
    async def write(
        self, value: Union[int, float], obj: BACnetObj, wait: bool = False, **kwargs: Any
    ) -> None:
        """You should implement async write method for your device."""

    async def write_with_check(
        self, value: Union[int, float], obj: BACnetObj, **kwargs: Any
    ) -> bool:
        """Writes value to object at controller and check it by read.

        Args:
            value: Value to write.
            obj: Objects instance.
            **kwargs:

        Returns:
            True - if write value and read value is consistent.
            False - if they aren't consistent.
        """
        self.interface.polling_event.clear()
        await self.write(value=value, obj=obj, **kwargs)
        _ = await self.read(obj=obj, wait=False, **kwargs)
        self.interface.polling_event.set()

        verified_obj = self._gtw.verifier.verify(obj=obj)
        read_value = verified_obj.present_value

        # hotfix
        await self._gtw._scheduler.spawn(self._gtw.send_objects(objs=[obj]))

        is_consistent = value == read_value
        self._LOG.debug(
            "Write with check called",
            extra={
                "device_id": obj.device_id,
                "object": obj,
                "value_written": value,
                "value_read": read_value,
                "values_are_consistent": is_consistent,
            },
        )
        return is_consistent

    @lru_cache(maxsize=10)
    def get_object(self, obj_id: int, obj_type_id: int) -> Optional[BACnetObj]:
        """Cache last 10 object instances.
        Args:
            obj_id: Object identifier.
            obj_type_id: Object type identifier.

        # todo: Implement binary search

        Returns:
            Object instance.
        """
        for obj in self.all_objects:
            if obj.type.type_id == obj_type_id and obj.id == obj_id:
                return obj
        return None

    def insert_objects(self, objs: Collection[BACnetObj]) -> None:
        """Groups objects by poll period and insert them into device for polling."""
        if objs:
            self.interface.polling_event.clear()
            for obj in objs:
                poll_period = obj.property_list.poll_period
                try:
                    self._objects[poll_period].add(obj)
                except KeyError:
                    self._objects[poll_period] = {obj}
            self.interface.polling_event.set()
            self._LOG.debug(
                "Objects are grouped by period and inserted to device",
                extra={"device_id": self.id, "objects_number": len(objs)},
            )

    async def start_periodic_polls(self) -> None:
        """Starts periodic polls for all periods."""

        if self.is_client_connected:
            self.interface.polling_event.set()
            for period, objs in self._objects.items():
                await self._scheduler.spawn(self.periodic_poll(objs=objs, period=period))
            await self._scheduler.spawn(self._periodic_reset_unreachable())
        else:
            self._LOG.info(
                "Client is not connected. Sleeping to next try",
                extra={
                    "device_id": self.id,
                    "seconds_to_next_try": self.reconnect_period,
                },
            )
            await asyncio.sleep(delay=self.reconnect_period)
            await self._gtw.async_add_job(self.create_client)
            await self._scheduler.spawn(self.start_periodic_polls())

    async def stop(self) -> None:
        """Waits for finish of all polling tasks with timeout, and stop polling.
        Closes client.
        """
        self.interface.polling_event.clear()
        await self._scheduler.close()
        await self.disconnect_client()
        self._LOG.info(
            "Device stopped",
            extra={
                "device_id": self.id,
            },
        )

    async def _periodic_reset_unreachable(self) -> None:
        await asyncio.sleep(self._gtw.settings.unreachable_reset_period)

        for objects in self._objects.values():
            for obj in objects:
                obj.unreachable_in_row = 0

        self._LOG.debug(
            "Reset unreachable objects",
            extra={
                "device_id": self.id,
            },
        )
        await self._scheduler.spawn(self._periodic_reset_unreachable())

    async def periodic_poll(
        self,
        objs: set[BACnetObj],
        period: float,
    ) -> None:
        self._LOG.debug(
            "Polling started",
            extra={
                "device_id": self.id,
                "period": period,
                "objects_number": len(objs),
            },
        )
        _t0 = datetime.now()
        await self._poll_objects(objs=objs)
        _t_delta = datetime.now() - _t0

        self._LOG.info(
            "Objects polled",
            extra={
                "device_id": self.id,
                "seconds_took": _t_delta.seconds,
                "objects_number": len(objs),
                "period": period,
            },
        )

        if _t_delta.seconds > period:
            self._LOG.warning("Polling period is too short!", extra={"device_id": self.id})
        await self._scheduler.spawn(self._after_polling_tasks(objs=objs))
        await asyncio.sleep(delay=period - _t_delta.seconds)

        # self._LOG.debug(f'Periodic polling task created',
        #                 extra={'device_id': self.id, 'period': period,
        #                        'jobs_active_count': self.scheduler.active_count,
        #                        'jobs_pending_count': self.scheduler.pending_count, })

        await self._scheduler.spawn(self.periodic_poll(objs=objs, period=period))

    async def _after_polling_tasks(self, objs: set[BACnetObj]) -> None:
        verified_objects = self._gtw.verifier.verify_objects(objs=objs)
        await self._gtw.send_objects(objs=verified_objects)

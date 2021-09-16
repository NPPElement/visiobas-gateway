import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Collection, Optional, Union

import aiojobs  # type: ignore
from pymodbus.client.asynchronous.async_io import AsyncioModbusSerialClient  # type: ignore
from pymodbus.client.sync import ModbusSerialClient  # type: ignore

from ..schemas import BACnetObj, DeviceObj, ObjType
from .base_device import BaseDevice

if TYPE_CHECKING:
    from ..gateway import Gateway
else:
    Gateway = "Gateway"


class BasePollingDevice(BaseDevice, ABC):
    """Base class for devices, that can be periodically polled for update sensors data."""

    _client_creation_lock: asyncio.Lock = None  # type: ignore

    # Key is serial port name.
    _serial_clients: dict[str, Union[ModbusSerialClient, AsyncioModbusSerialClient]] = {}
    _serial_port_locks: dict[str, asyncio.Lock] = {}
    _serial_polling: dict[str, asyncio.Event] = {}
    _serial_connected: dict[str, bool] = {}

    def __init__(self, device_obj: DeviceObj, gateway: Gateway):
        super().__init__(device_obj, gateway)

        self._scheduler: aiojobs.Scheduler = None  # type: ignore

        # Key: period
        self._objects: dict[float, set[BACnetObj]] = {}
        self._unreachable_objects: set[BACnetObj] = set()
        # self._nonexistent_objects: set[BACnetObj] = set()

        self._connected = False

        # IMPORTANT: clear that event to change the objects (load or priority write).
        # Wait that event in polling to provide priority access to write_with_check.
        self._polling = asyncio.Event()

    @property
    def is_client_connected(self) -> bool:
        if self.serial_port:
            return bool(self._serial_connected.get(self.serial_port))
        return self._connected

    @classmethod
    async def create(cls, device_obj: DeviceObj, gateway: Gateway) -> "BasePollingDevice":
        dev = cls(device_obj=device_obj, gateway=gateway)
        dev._scheduler = await aiojobs.create_scheduler(close_timeout=60, limit=100)

        if not isinstance(cls._client_creation_lock, asyncio.Lock):
            cls._client_creation_lock = asyncio.Lock(loop=gateway.loop)

        async with cls._client_creation_lock:  # pylint: disable=not-async-context-manager
            await dev._gtw.async_add_job(dev.create_client)
        dev._LOG.debug(
            "Device created",
            extra={
                "device_id": dev.device_id,
                "protocol": dev.protocol,
                "serial_clients_dict": cls._serial_clients,
            },
        )
        return dev

    @property
    def serial_port(self) -> Optional[str]:
        if hasattr(self._dev_obj.property_list, "rtu"):
            return self._dev_obj.property_list.rtu.port  # type: ignore
        return None

    @property
    def _polling_event(self) -> asyncio.Event:
        port = self.serial_port
        if port:
            return self._serial_polling[port]
        return self._polling

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
    def all_objects(self) -> set[BACnetObj]:
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
    async def _poll_objects(self, objs: Collection[BACnetObj]) -> None:
        raise NotImplementedError

    @abstractmethod
    async def read(
        self, obj: BACnetObj, wait: bool = False, **kwargs: Any
    ) -> Optional[Union[int, float, str]]:
        raise NotImplementedError("You should implement async read method for your device")

    @abstractmethod
    async def write(
        self, value: Union[int, float], obj: BACnetObj, wait: bool = False, **kwargs: Any
    ) -> None:
        raise NotImplementedError("You should implement async write method for your device")

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
        self._polling_event.clear()
        await self.write(value=value, obj=obj, **kwargs)
        read_value = await self.read(obj=obj, wait=False, **kwargs)
        self._polling_event.set()

        is_consistent = value == read_value
        self._LOG.debug(
            "Write with check called",
            extra={
                "device_id": obj.device_id,
                "object_id": obj.id,
                "object_type": obj.type,
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

        # todo: Implement binary search?

        Returns:
            Object instance.
        """
        for obj in self.all_objects:
            if obj.type.type_id == obj_type_id and obj.id == obj_id:
                return obj
        return None

    def insert_objects(self, objs: Collection[BACnetObj]) -> None:
        """Groups objects by poll period and insert them into device for polling."""
        if len(objs):
            self._polling_event.clear()
            for obj in objs:
                poll_period = obj.property_list.poll_period
                try:
                    self._objects[poll_period].add(obj)
                except KeyError:
                    self._objects[poll_period] = {obj}
            self._polling_event.set()
            self._LOG.debug(
                "Objects are grouped by period and inserted to device",
                extra={"device_id": self.device_id, "objects_number": len(objs)},
            )

    async def start_periodic_polls(self) -> None:
        """Starts periodic polls for all periods."""

        if self.is_client_connected:
            self._polling_event.set()
            for period, objs in self._objects.items():
                await self._scheduler.spawn(
                    self.periodic_poll(objs=objs, period=period, first_iter=True)
                )
            await self._scheduler.spawn(self._periodic_reset_unreachable())
        else:
            self._LOG.info(
                "Client is not connected. Sleeping to next try",
                extra={
                    "device_id": self.device_id,
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
        self._polling_event.clear()
        await self._scheduler.close()
        self.close_client()  # todo: left client open if used by another device
        self._LOG.info(
            "Device stopped",
            extra={
                "device_id": self.device_id,
            },
        )

    async def _periodic_reset_unreachable(self) -> None:
        await asyncio.sleep(self._gtw.unreachable_reset_period)

        self._LOG.debug(
            "Reset unreachable objects",
            extra={
                "device_id": self.device_id,
                "unreachable_objects_number": len(self._unreachable_objects),
            },
        )
        self.insert_objects(objs=self._unreachable_objects)
        self._unreachable_objects = set()

        await self._scheduler.spawn(self._periodic_reset_unreachable())

    async def periodic_poll(
        self,
        objs: set[BACnetObj],
        period: float,
        *,
        first_iter: bool = False,
    ) -> None:
        self._LOG.debug(
            "Polling started",
            extra={
                "device_id": self.device_id,
                "period": period,
                "objects_number": len(objs),
            },
        )
        _t0 = datetime.now()
        await self._poll_objects(objs=objs)
        self._check_unreachable(objs=objs, period=period)  # hotfix
        if first_iter:
            nonexistent_objs = {obj for obj in objs if not obj.existing}
            objs -= nonexistent_objs
            self._LOG.info(
                "Removed non-existent objects",
                extra={
                    "device_id": self.device_id,
                    "nonexistent_objects": nonexistent_objs,
                    "nonexistent_objects_number": len(nonexistent_objs),
                },
            )

        _t_delta = datetime.now() - _t0
        self._LOG.info(
            "Objects polled",
            extra={
                "device_id": self.device_id,
                "seconds_took": _t_delta.seconds,
                "objects_number": len(objs),
                "period": period,
            },
        )

        if _t_delta.seconds > period:
            # period *= 1.5
            self._LOG.warning(
                "Polling period is too short!", extra={"device_id": self.device_id}
            )
        await self._scheduler.spawn(self._process_polled(objs=objs))
        await asyncio.sleep(delay=period - _t_delta.seconds)

        # self._LOG.debug(f'Periodic polling task created',
        #                 extra={'device_id': self.id, 'period': period,
        #                        'jobs_active_count': self.scheduler.active_count,
        #                        'jobs_pending_count': self.scheduler.pending_count, })

        await self._scheduler.spawn(self.periodic_poll(objs=objs, period=period))

    async def _process_polled(self, objs: set[BACnetObj]) -> None:
        await self._gtw.verify_objects(objs=objs)
        await self._gtw.send_objects(objs=objs)

    def _check_unreachable(self, objs: set[BACnetObj], period: float) -> None:
        for obj in objs.copy():
            if obj.unreachable_in_row >= self._gtw.unreachable_threshold:
                self._LOG.debug(
                    "Marked as unreachable",
                    extra={
                        "device_id": obj.device_id,
                        "object_id": obj.id,
                        "object_type": obj.type,
                    },
                )
                self._objects[period].remove(obj)
                self._unreachable_objects.add(obj)

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from functools import lru_cache, wraps
from time import time
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Collection, Iterable

import aiojobs  # type: ignore

from ..schemas import OUTPUT_TYPES, STRICT_OUTPUT_TYPES, BACnetObj, DeviceObj
from ..utils import get_file_logger, log_exceptions
from ._interface import Interface, InterfaceKey
from .base_device import BaseDevice

if TYPE_CHECKING:
    from ..gateway import Gateway
else:
    Gateway = "Gateway"

ObjectKey = tuple[int, int]  # obj_id, obj_type_id

_LOG = get_file_logger(name=__name__)


class AbstractBasePollingDevice(BaseDevice, ABC):
    """Base class for devices, that can be periodically polled for update sensors data."""

    _interfaces: dict[InterfaceKey, Interface] = {}

    def __init__(self, device_obj: DeviceObj, gateway: Gateway):
        super().__init__(device_obj, gateway)

        self._scheduler: aiojobs.Scheduler = None  # type: ignore
        self.object_groups: dict[float, dict[ObjectKey, BACnetObj]] = {}  # Key: period

    @staticmethod
    @abstractmethod
    async def is_reachable(device_obj: DeviceObj) -> bool:
        """Check device interface is available to interaction."""

    @property
    def interface(self) -> Interface:
        """Interface to interact with controller."""
        return self.__class__._interfaces[  # pylint: disable=protected-access
            self.interface_key(device_obj=self._device_obj)
        ]

    @staticmethod
    @abstractmethod
    def interface_key(
        device_obj: DeviceObj,
    ) -> InterfaceKey:
        """Hashable interface key to interaction with device with lock.
        Used as key in interfaces `dict`.
        """

    @classmethod
    @log_exceptions(logger=_LOG)
    async def create(
        cls, device_obj: DeviceObj, gateway: Gateway
    ) -> AbstractBasePollingDevice:
        """Creates instance of device. Handles client creation with lock or using
        existing.
        """
        interface_key = cls.interface_key(device_obj=device_obj)
        if not await cls.is_reachable(device_obj=device_obj):
            raise EnvironmentError(f"{device_obj.property_list.interface} is unreachable")
        _LOG.debug(
            "Interface reachable",
            extra={"interface": interface_key, "used_interfaces": cls._interfaces},
        )

        device = cls(device_obj=device_obj, gateway=gateway)
        device._scheduler = await aiojobs.create_scheduler(close_timeout=60, limit=None)

        if interface_key not in cls._interfaces:
            lock = asyncio.Lock(loop=gateway.loop)
            async with lock:  # pylint: disable=not-async-context-manager
                client = await device.create_client(device_obj=device_obj)
                client_connected = await device.connect_client(client=client)
            polling_event = asyncio.Event()
            interface = Interface(
                interface_key=interface_key,
                used_by={device.id},
                client=client,
                lock=lock,
                polling_event=polling_event,
                client_connected=client_connected,
            )
            cls._interfaces[interface_key] = interface
        else:
            # Using existing interface.
            cls._interfaces[interface_key].used_by.add(device.id)

        device._LOG.debug(
            "Device created",
            extra={"device": device, "used_interfaces": cls._interfaces.items()},
        )
        return device

    @property
    def reconnect_period(self) -> int:
        return self._device_obj.property_list.reconnect_period

    @abstractmethod
    async def create_client(self, device_obj: DeviceObj) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def connect_client(self, client: Any) -> bool:
        """Performs connect with client."""

    async def disconnect_client(self) -> None:
        interface = self.interface
        if not interface.used_by:
            await self._disconnect_client(client=interface.client)

    @abstractmethod
    async def _disconnect_client(self, client: Any) -> None:
        """Performs disconnect with client."""

    @property
    @abstractmethod
    def is_client_connected(self) -> bool:
        """Checks that client is connected."""

    async def poll_objects(
        self, objs: Iterable[BACnetObj], unreachable_threshold: int
    ) -> list[BACnetObj]:
        """Sorts actual objects and polls them."""
        actual_objs = [
            obj
            for obj in objs
            if obj.existing and obj.unreachable_in_row < unreachable_threshold
        ]
        objs_polling_tasks = [self.read_objects(objs=actual_objs)]
        polled_objs = await asyncio.gather(*objs_polling_tasks)
        return list(polled_objs)

    @abstractmethod
    async def read_single_object(self, obj: BACnetObj, **kwargs: Any) -> BACnetObj:
        """ """

    @abstractmethod
    async def write_single_object(
        self, value: int | float | str, obj: BACnetObj, **kwargs: Any
    ) -> None:
        """ """

    @abstractmethod
    async def read_objects(
        self, objs: Collection[BACnetObj], **kwargs: Any
    ) -> Collection[BACnetObj]:
        """ """

    @abstractmethod
    async def write_objects(
        self, values: list[int | float | str], objs: Collection[BACnetObj]
    ):
        """ """

    @log_exceptions(logger=_LOG)
    async def write_with_check(
        self, value: int | float | str, output_obj: BACnetObj, **kwargs: Any
    ) -> tuple[BACnetObj, BACnetObj | None]:
        """Writes value to object at controller and check it by read.

        Args:
            value: Value to write.
            output_obj: ...Output | ...Value object instance.
            **kwargs:

        Returns:
            Verified output object instance | tuple of two verified object instances:
            output and mapped input.

        # todo: refactor?
        """
        if output_obj.object_type not in OUTPUT_TYPES:
            raise ValueError(
                f"Expected object with type one of: {OUTPUT_TYPES}. "
                f"Got {output_obj.object_type}"
            )

        need_synchronize = output_obj.object_type in STRICT_OUTPUT_TYPES

        input_obj = (
            self.get_object(
                object_id=output_obj.object_id,
                object_type_id=output_obj.object_type.value - 1,
            )
            if need_synchronize
            else None
        )

        self.interface.polling_event.clear()
        await self.write_single_object(value=value, obj=output_obj, **kwargs)

        # Several devices process write requests with delay.
        # Wait processing on device side to get actual data.
        await asyncio.sleep(1)

        polled_output_obj = await self.read_objects(obj=output_obj, wait=False, **kwargs)
        polled_input_obj = (
            await self.read_objects(obj=input_obj, wait=False, **kwargs)
            if input_obj
            else None
        )
        self.interface.polling_event.set()

        verified_output_obj = self._gateway.verifier.verify(obj=polled_output_obj)
        verified_input_obj = (
            self._gateway.verifier.verify(obj=polled_input_obj)
            if polled_input_obj
            else None
        )
        self._LOG.debug(
            "Write with check called",
            extra={
                "output_object": verified_output_obj,
                "input_object": verified_input_obj,
                "value_write": value,
            },
        )
        return verified_output_obj, verified_input_obj

    @lru_cache(maxsize=10)
    def get_object(self, object_id: int, object_type_id: int) -> BACnetObj | None:
        """Cache last 10 object instances.
        Args:
            object_id: Object identifier.
            object_type_id: Object type identifier.

        Returns:
            Object instance.

        fixme: use dict
        """
        for obj_group in self.object_groups.values():
            if (object_id, object_type_id) in obj_group:
                return obj_group[(object_id, object_type_id)]
        return None

    @log_exceptions(logger=_LOG)
    async def start_periodic_polls(self) -> None:
        """Starts periodic polls for all periods."""

        if self.is_client_connected:
            self.interface.polling_event.set()
            for period, objs_group in self.object_groups.items():
                self._LOG.debug(
                    "Spawning polling task for objects group",
                    extra={
                        "device_id": self.id,
                        "period": period,
                        "objects_quantity": len(objs_group.values()),
                    },
                )
                await self._scheduler.spawn(
                    self.periodic_poll(objs=objs_group.values(), period=period)
                )
            await self._scheduler.spawn(
                self._periodic_reset_unreachable(self.object_groups)
            )
        else:
            self._LOG.info(
                "Client is not connected. Sleeping to next try",
                extra={"device_id": self.id, "seconds_to_next_try": self.reconnect_period},
            )
            await asyncio.sleep(delay=self.reconnect_period)
            self.__class__._interfaces[  # pylint: disable=protected-access
                self.interface_key(device_obj=self._device_obj)
            ].client = await self.create_client(self._device_obj)
            await self._scheduler.spawn(self.start_periodic_polls())

    async def stop(self) -> None:
        """Waits for finish of all polling tasks with timeout, and stop polling.
        Closes client.
        """
        self.interface.polling_event.clear()
        await self._scheduler.close()
        await self.disconnect_client()
        self._LOG.info("Device stopped", extra={"device_id": self.id})

    async def _periodic_reset_unreachable(
        self, object_groups: dict[float, dict[tuple[int, int], BACnetObj]]
    ) -> None:
        await asyncio.sleep(self._gateway.settings.unreachable_reset_period)

        for objs_group in object_groups.values():
            for obj in objs_group.values():
                obj.unreachable_in_row = 0

        self._LOG.debug("Reset unreachable objects", extra={"device_id": self.id})
        await self._scheduler.spawn(
            self._periodic_reset_unreachable(object_groups=object_groups)
        )

    @log_exceptions(logger=_LOG)
    async def periodic_poll(
        self,
        objs: Collection[BACnetObj],
        period: float,
    ) -> None:
        self._LOG.debug(
            "Polling started",
            extra={"device_id": self.id, "period": period, "objects_number": len(objs)},
        )
        _t0 = time()
        polled_objs = await self.poll_objects(
            objs=objs, unreachable_threshold=self._gateway.settings.unreachable_threshold
        )
        _t_delta = int(time() - _t0)
        self._LOG.info(
            "Objects polled",
            extra={
                "device_id": self.id,
                "seconds_took": _t_delta,
                "objects_quantity": len(polled_objs),
                "period": period,
            },
        )
        if _t_delta > period:
            self._LOG.warning("Polling period is too short!", extra={"device_id": self.id})
        verified_objs = await self._after_polling_tasks(objs=polled_objs)
        await asyncio.sleep(delay=period - _t_delta)
        await self._scheduler.spawn(self.periodic_poll(objs=verified_objs, period=period))

    async def _after_polling_tasks(self, objs: list[BACnetObj]) -> list[BACnetObj]:
        verified_objects = self._gateway.verifier.verify_objects(objs=objs)
        await self._scheduler.spawn(self._gateway.send_objects(objs=verified_objects))
        return verified_objects

    @staticmethod
    def wait_access(func: Callable | Callable[..., Awaitable]) -> Any:
        @wraps(func)
        async def wrapper(
            self: AbstractBasePollingDevice, *args: Any, **kwargs: Any
        ) -> Any:
            await self.interface.polling_event.wait()
            return func(*args, **kwargs)

        return wrapper

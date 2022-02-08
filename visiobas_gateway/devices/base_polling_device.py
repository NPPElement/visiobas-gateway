from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from functools import lru_cache, wraps
from time import time
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Collection,
    Iterable,
    Iterator,
    Sequence,
)

import aiojobs  # type: ignore

from ..schemas import OUTPUT_TYPES, STRICT_OUTPUT_TYPES, BACnetObj, DeviceObj
from ..utils import get_file_logger, log_exceptions
from ._interface import Interface, InterfaceKey
from .base_device import BaseDevice

if TYPE_CHECKING:
    from ..gateway import Gateway
else:
    Gateway = Any

ObjectKey = tuple[int, int]  # obj_id, obj_type_id

_LOG = get_file_logger(name=__name__)


class AbstractBasePollingDevice(BaseDevice, ABC):
    """Base class for devices, that can be periodically polled for update sensors data."""

    _interfaces: dict[InterfaceKey, Interface] = {}

    # FIXME: issue with set exceptions to objects
    # FIXME: issue with objects check (write - only output types)

    def __init__(self, device_obj: DeviceObj, gateway: Gateway):
        super().__init__(device_obj, gateway)

        self._scheduler: aiojobs.Scheduler = None  # type: ignore
        self.object_groups: dict[float, dict[ObjectKey, BACnetObj]] = {}  # Key: period

        # Decorated `read_single_object` to set exception to object.
        setattr(self, "read_single_object", self._set_exception(self.read_single_object))
        # Decorated `write_single_object` to check object type.
        setattr(
            self,
            "write_single_object",
            self._check_output_object_type(self.write_single_object),
        )

        # todo: Refactor: use priority queue?
        # Decorated read methods with priority.
        # They should be executed after write in `write_with_check` method without delays.
        # For that purpose creating copy of methods with priority access.
        self.priority_read_single_object = self._acquire_access(
            self.read_single_object, device=self
        )
        self.priority_read_multiple_objects = self._acquire_access(
            self.read_multiple_objects, device=self
        )
        # Write methods should be executed as fast as possible.
        # So they always call with priority access.
        #
        # For that purpose decorating them by `AbstractBasePollingDevice._acquire_access`
        # write protocol-specific requests in `create_client` method.
        #
        # Read methods should wait to execute. For that purpose decorating them by
        # `AbstractBasePollingDevice._wait_access` in `create_client` method.

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

        if interface_key in cls._interfaces:
            # Using existing client.
            cls._interfaces[interface_key].used_by.add(device.id)
        else:
            # Creating client for interface
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
        """Creates client for device.

        Note: All blocking methods should be decorated here.
        """

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
        actual_objs: list[BACnetObj] = [
            obj
            for obj in objs
            if obj.existing and obj.unreachable_in_row < unreachable_threshold
        ]
        multiple_objs: list[BACnetObj] = []
        single_objs: list[BACnetObj] = []
        for obj in actual_objs:
            if obj.segmentation_supported:
                multiple_objs.append(obj)
            else:
                single_objs.append(obj)

        chunked_objs: list[Sequence[BACnetObj]] = []
        for chunk in self._get_chunk_for_multiple(objs=multiple_objs):
            if len(chunk) == 1:
                single_objs.append(chunk[0])
            else:
                chunked_objs.append(chunk)
        _LOG.debug("Objects to poll", extra={"objects_count": len(actual_objs)})
        group_single = [self.read_single_object(obj=obj) for obj in single_objs]
        group_multiple = [self.read_multiple_objects(objs=objs) for objs in chunked_objs]

        results = await asyncio.gather(*group_single, *group_multiple)

        polled_objs: list[BACnetObj] = []
        for result in results:
            # if isinstance(result, BaseException):
            #     continue
            if isinstance(result, BACnetObj):
                polled_objs.append(result)
            elif isinstance(result, Sequence):
                polled_objs.extend(list(result))
        return polled_objs

    @abstractmethod
    async def read_single_object(self, *, obj: BACnetObj, **kwargs: Any) -> BACnetObj:
        """Reads properties of single object."""

    @abstractmethod
    async def write_single_object(
        self, value: int | float | str, *, obj: BACnetObj, **kwargs: Any
    ) -> None:
        """Writes property to single object."""

    @abstractmethod
    async def read_multiple_objects(
        self, objs: Sequence[BACnetObj], **kwargs: Any
    ) -> Sequence[BACnetObj]:
        """Reads properties form one or multiple objects."""

    @staticmethod
    @abstractmethod
    def _get_chunk_for_multiple(objs: Sequence[BACnetObj]) -> Iterator:
        """
        Returns:
            Iterator for objects' sequences needed size for `read_multiple_objects`
            requests.
        """

    @abstractmethod
    async def write_multiple_objects(
        self, values: list[int | float | str], objs: Sequence[BACnetObj]
    ) -> None:
        """Writes properties to one or multiple objects."""

    @log_exceptions(logger=_LOG)
    async def write_with_check(
        self, value: int | float | str, output_obj: BACnetObj, **kwargs: Any
    ) -> list[BACnetObj]:
        """Writes value to object at controller and check it by read.

        Args:
            value: Value to write.
            output_obj: ...Output | ...Value object instance.
            **kwargs:

        Returns:
            Verified output object instance | tuple of two verified object instances:
            output and mapped input.
        """

        await self.write_single_object(value=value, obj=output_obj, **kwargs)
        # Several devices process write requests with delay.
        # Wait processing on device side to get actual data.
        await asyncio.sleep(1)

        need_synchronize = output_obj.object_type in STRICT_OUTPUT_TYPES
        if need_synchronize:
            input_obj = self.get_object(
                object_id=output_obj.object_id,
                object_type_id=output_obj.object_type.value - 1
                # ANY_INPUT_TYPE always has value ANY_OUTPUT_TYPE - 1
            )
            objs = [output_obj, input_obj]
        else:
            objs = [output_obj]

        polling_tasks = [self.priority_read_multiple_objects(objs=objs, **kwargs)]
        polled_objs = await asyncio.gather(*polling_tasks)
        polled_objs = [obj for obj in polled_objs if isinstance(obj, BACnetObj)]

        verified_objs = await self._after_polling_tasks(objs=polled_objs)
        self._LOG.debug(
            "Write with check called",
            extra={
                "need_synchronize": need_synchronize,
                "objects": objs,
                "verified_objects": verified_objs,
                "value_write": value,
            },
        )
        return verified_objs

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
                    self._periodic_poll(objs=objs_group.values(), period=period)
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
    async def _periodic_poll(
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
        _time_delta = int(time() - _t0)
        self._LOG.info(
            "Objects polled",
            extra={
                "device_id": self.id,
                "seconds_took": _time_delta,
                "objects_quantity": len(polled_objs),
                "period": period,
            },
        )
        if _time_delta > period:
            self._LOG.warning("Polling period is too short!", extra={"device_id": self.id})
        verified_objs = await self._after_polling_tasks(objs=polled_objs)
        await asyncio.sleep(delay=period - _time_delta)
        await self._scheduler.spawn(self._periodic_poll(objs=verified_objs, period=period))

    async def _after_polling_tasks(self, objs: list[BACnetObj]) -> list[BACnetObj]:
        verified_objects = self._gateway.verifier.verify_objects(objs=objs)
        await self._scheduler.spawn(self._gateway.send_objects(objs=verified_objects))
        return verified_objects

    @staticmethod
    def _set_exception(func: Callable[..., Awaitable]) -> Callable[..., Awaitable]:
        """Decorated read methods to set exceptions to object if they occurs."""

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as exc:  # pylint: disable=broad-except
                obj: BACnetObj = kwargs["obj"]
                obj.set_property(value=exc)

        return async_wrapper

    @staticmethod
    def _check_output_object_type(
        func: Callable[..., Awaitable]
    ) -> Callable[..., Awaitable]:
        """
        Raises:
            ValueError: If object cannot be writen.

        Note: Should be used in write methods.
        """

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # pylint: disable=unused-argument
            obj = kwargs["obj"]
            if obj.object_type not in OUTPUT_TYPES:
                raise ValueError(
                    f"Cannot write object. Expected object type one of: {OUTPUT_TYPES}. "
                    f"Got `{obj.object_type}`"
                )

        return async_wrapper

    @staticmethod
    def _wait_access(
        func: Callable | Callable[..., Awaitable], device: AbstractBasePollingDevice
    ) -> Callable[..., Awaitable]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            await device.interface.polling_event.wait()
            if asyncio.iscoroutine(func) or asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return func(*args, **kwargs)

        return wrapper

    @staticmethod
    def _acquire_access(
        func: Callable | Callable[..., Awaitable], device: AbstractBasePollingDevice
    ) -> Callable | Callable[..., Awaitable]:

        if asyncio.iscoroutine(func) or asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                device.interface.polling_event.clear()
                result = await func(*args, **kwargs)
                device.interface.polling_event.set()
                return result

            return async_wrapper

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            device.interface.polling_event.clear()
            result = func(*args, **kwargs)
            device.interface.polling_event.set()
            return result

        return sync_wrapper

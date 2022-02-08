from __future__ import annotations

import asyncio
from functools import lru_cache
from ipaddress import IPv4Address
from typing import Any, Collection, Iterator, Sequence

from BAC0.core.io.IOExceptions import (  # type: ignore
    ReadPropertyMultipleException,
    SegmentationNotSupported,
)
from BAC0.scripts.Lite import Lite  # type: ignore

from ...schemas import BACnetObj, DeviceObj, ObjProperty, TcpDevicePropertyList
from ...utils import camel_case, get_file_logger, get_subnet_interface, log_exceptions, ping
from .._interface import InterfaceKey
from ..base_polling_device import AbstractBasePollingDevice
from ._bacnet_coder_mixin import BACnetCoderMixin

_LOG = get_file_logger(name=__name__)

# Optimal objects per RPM requests
_READ_PROPERTY_MULTIPLE_CHUNK_SIZE = 25


class BACnetDevice(AbstractBasePollingDevice, BACnetCoderMixin):
    """Implementation of BACnet device client."""

    # todo: use COV subscribe?

    @staticmethod
    @lru_cache(maxsize=100)
    def interface_key(device_obj: DeviceObj) -> InterfaceKey:
        if isinstance(device_obj.property_list, TcpDevicePropertyList):
            ip = device_obj.property_list.ip
            ip_in_subnet = get_subnet_interface(ip=ip)
            if ip_in_subnet:
                return ip_in_subnet
            raise EnvironmentError(f"No IP in same subnet with {ip}")
        raise ValueError(
            f"`TcpDevicePropertyList` expected. Got {device_obj.property_list}."
        )

    @property
    def is_client_connected(self) -> bool:
        return bool(self.interface.client)

    @staticmethod
    async def is_reachable(device_obj: DeviceObj) -> bool:
        if isinstance(device_obj.property_list, TcpDevicePropertyList):
            ping_result = await ping(host=str(device_obj.property_list.ip), attempts=4)
            _LOG.debug(
                "Ping completed",
                extra={"ping_result": ping_result, "device_obj": device_obj},
            )
            return ping_result
        raise ValueError(
            f"`TcpDevicePropertyList` expected. Got {device_obj.property_list}."
        )

    @log_exceptions(logger=_LOG)
    async def create_client(self, device_obj: DeviceObj) -> Lite:
        """
        Return: BAC0 client with decorated priority write methods.
        """

        ip, port = device_obj.property_list.interface
        if not isinstance(ip, IPv4Address):
            raise ValueError(f"`IPv4Address` expected. Got `{type(ip)}`")

        ip_in_subnet = get_subnet_interface(ip=ip)
        if not ip_in_subnet:
            raise EnvironmentError(f"No IP in same subnet with {ip}")

        self._LOG.debug(
            "Creating `BAC0` client",
            extra={"device_id": self.id, "ip_in_subnet": ip_in_subnet},
        )
        client = Lite(ip=str(ip_in_subnet), port=port)

        # Decorating write methods for priority access.
        client.write = AbstractBasePollingDevice._acquire_access(client.write, device=self)
        client.writeMultiple = AbstractBasePollingDevice._acquire_access(
            client.writeMultiple, device=self
        )
        # Read methods must execute after write requests.
        client.read = AbstractBasePollingDevice._wait_access(client.read, device=self)
        client.readMultiple = AbstractBasePollingDevice._wait_access(
            client.readMultiple, device=self
        )
        return client

    async def connect_client(self, client: Any) -> bool:
        if isinstance(client, Lite):
            return True
        return False

    async def _disconnect_client(self, client: Lite) -> None:
        client.disconnect()

    @log_exceptions(logger=_LOG)
    async def _write_property(
        self, value: int | float | str, obj: BACnetObj, prop: ObjProperty, priority: int
    ) -> bool | None:
        """Writes value to property value in object.

        Args:
            value: Value to write.
            obj: Object instance.
            prop: Property which write.
            priority: Value priority.

        Returns:
            Write is successful.
        """
        if self._is_binary_obj(obj=obj) and prop is ObjProperty.PRESENT_VALUE:
            value = self._encode_binary_present_value(value=value)  # type: ignore

        args = (
            f"{self.device_address} "
            f"{camel_case(obj.object_type.name)} "
            f"{obj.object_id} "
            f"{camel_case(prop.name)} "
            f"{value} "
            f"- {priority}"
        )
        success = await self.interface.client.write(args=args)
        self._LOG.debug(
            "Write property",
            extra={"device_id": self.id, "object": obj, "value": value, "success": success},
        )
        return success

    async def _read_property(self, obj: BACnetObj, prop: ObjProperty) -> BACnetObj:
        request = " ".join(
            (
                self.device_address,
                camel_case(obj.object_type.name),
                str(obj.object_id),
                camel_case(prop.name),
            )
        )
        response = await self.interface.client.read(request)
        self._LOG.debug(
            "Read property",
            extra={"device_id": self.id, "object": obj, "response": response},
        )
        if prop is ObjProperty.PRIORITY_ARRAY:
            response = self._decode_priority_array(priority_array=response)

        obj.set_property(value=response, prop=prop)
        return obj

    async def _read_property_multiple(
        self, objs: Sequence[BACnetObj]
    ) -> Sequence[BACnetObj]:
        """ """
        if len(objs) > _READ_PROPERTY_MULTIPLE_CHUNK_SIZE:
            _LOG.warning(
                "Large number of objects in RPM request can lead to request segmentation. "
                "It leads to slow execution.",
                extra={
                    "object_count": len(objs),
                    "optimal_rpm_chunk_size": _READ_PROPERTY_MULTIPLE_CHUNK_SIZE,
                },
            )

        request_dict = {
            "address": self.device_address,
            "objects": self._get_objects_rpm_dict(objs=objs),
        }
        response = await self.interface.client.readMultiple(request_dict=request_dict)
        self._LOG.debug(
            "Read property multiple",
            extra={"device_id": self.id, "objects": objs, "response": response},
        )
        for obj in objs:
            object_key = f"{camel_case(obj.object_type.name)}:{obj.object_id}"
            values: list[tuple[str, Any]] = response[object_key]
            for v, prop in zip(values, obj.polling_properties):
                # v example: ('presentValue', 4.233697891235352),
                if prop is ObjProperty.PRIORITY_ARRAY:
                    v = self._decode_priority_array(priority_array=v[1])  # type: ignore
                    # fixme: issue with type
                obj.set_property(value=v, prop=prop)

        return objs

    async def _read_all_properties(self, obj: BACnetObj) -> BACnetObj:
        """Simulates `read_property_multiple` with `read_property` by sending requests
        for each property separately. It works slowly. Used for devices not
        supported `read_property_multiple`.

        Note: Each used `read_property` has wait so, don't use wait here.
        """
        for prop in obj.polling_properties:
            try:
                obj = await self._read_property(obj=obj, prop=prop)
            except Exception as exc:  # pylint: disable=broad-except
                # obj.set_property(value=exc)
                self._LOG.warning(
                    "Read error",
                    extra={"object": obj, "property": prop, "exception": exc},
                    exc_info=True,
                )
        return obj

    async def read_single_object(self, *, obj: BACnetObj, **kwargs: Any) -> BACnetObj:
        _LOG.debug("Reading single object")
        if obj.segmentation_supported:
            # Polling only one object, so just use [0] index.
            try:
                return (await self._read_property_multiple(objs=[obj]))[0]
            except (  # pylint: disable=broad-except
                SegmentationNotSupported,
                ReadPropertyMultipleException,
                Exception,
            ) as e:
                obj.segmentation_supported = False
                _LOG.debug(
                    "Segmentation not supported",
                    extra={"object": obj, "exception": e},
                    exc_info=True,
                )

        return await self._read_all_properties(obj=obj)

    async def write_single_object(
        self,
        value: int | float | str,
        *,
        obj: BACnetObj,
        **kwargs: Any,
    ) -> None:
        prop = kwargs["prop"]
        priority = kwargs["priority"]
        await self._write_property(value, obj, prop, priority)

    async def read_multiple_objects(
        self, objs: Sequence[BACnetObj], **kwargs: Any
    ) -> Sequence[BACnetObj]:
        try:
            return await self._read_property_multiple(objs=objs)
        except (  # pylint: disable=broad-except
            SegmentationNotSupported,
            ReadPropertyMultipleException,
            Exception,
        ) as e:
            _LOG.debug(
                "Read multiple failed. Reading by single requests", extra={"exception": e}
            )
            read_single_tasks = [self.read_single_object(obj=obj) for obj in objs]
            polled_objs = await asyncio.gather(*read_single_tasks)
            polled_objs = [obj for obj in polled_objs if isinstance(obj, BACnetObj)]
            return polled_objs

    async def write_multiple_objects(
        self, values: list[int | float | str], objs: Collection[BACnetObj]
    ) -> None:
        """Not used now."""
        raise NotImplementedError

    @staticmethod
    def _get_chunk_for_multiple(objs: Sequence[BACnetObj]) -> Iterator:

        for i in range(0, len(objs), _READ_PROPERTY_MULTIPLE_CHUNK_SIZE):
            yield objs[i : i + _READ_PROPERTY_MULTIPLE_CHUNK_SIZE]  # noqa

    @property
    def device_address(self) -> str:
        """Returns address in format 'ip_address:port'."""
        return ":".join([str(item) for item in self._device_obj.property_list.interface])

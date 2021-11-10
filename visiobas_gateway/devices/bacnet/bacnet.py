from __future__ import annotations

from functools import lru_cache
from ipaddress import IPv4Address
from typing import Any

from BAC0.core.io.IOExceptions import ReadPropertyMultipleException  # type: ignore
from BAC0.scripts.Lite import Lite  # type: ignore

from ...schemas import BACnetObj, DeviceObj, ObjProperty, TcpDevicePropertyList
from ...utils import camel_case, get_file_logger, get_subnet_interface, log_exceptions, ping
from .._interface import InterfaceKey
from ..base_polling_device import AbstractBasePollingDevice
from ._bacnet_coder_mixin import BACnetCoderMixin

_LOG = get_file_logger(name=__name__)


class BACnetDevice(AbstractBasePollingDevice, BACnetCoderMixin):
    """Implementation of BACnet device client."""

    # def __init__(self, device_obj: BACnetDeviceObj, gateway: Gateway):
    #     super().__init__(device_obj, gateway)
    #
    #     self._device_obj: BACnetDeviceObj
    #
    #     self.support_rpm: set[BACnetObj] = set()
    #     self.not_support_rpm: set[BACnetObj] = set()
    #
    #     # self.__objects_per_rpm = 25
    #     # todo: Should we use one RPM for several objects?
    #     # todo: use COV subscribe

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
        """Initializes BAC0 client."""

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
        return client

    async def connect_client(self, client: Any) -> bool:
        if isinstance(client, Lite):
            return True
        return False

    async def _disconnect_client(self, client: Lite) -> None:
        client.disconnect()

    # def poll(self) -> None:
    #     """ Poll all object from device.
    #         Send each object into verifier after answer.
    #         When all objects polled, send device_id into verifier as finish signal
    #     """
    #     for obj in self.support_rpm:
    #         assert isinstance(obj, BACnetObject)
    #
    #         self.__logger.debug(f'Polling supporting PRM {obj} ...')
    #         try:
    #             values = self.rpm(obj=obj)
    #             self.__logger.debug(f'{obj} values: {values}')
    #         except ReadPropertyMultipleException as e:
    #             self.__logger.warning(f'{obj} rpm error: {e}\n'
    #                                   f'{obj} Marking as not supporting RPM ...')
    #             self.not_support_rpm.add(obj)
    #             # self.support_rpm.discard(obj)
    #
    #         except Exception as e:
    #             self.__logger.error(f'{obj} polling error: {e}', exc_info=True)
    #         else:
    #             self.__logger.debug(f'From {obj} read: {values}. Sending to verifier ...')
    #             self.__put_data_into_verifier(properties=values)
    #
    #     self.support_rpm.difference_update(self.not_support_rpm)
    #
    #     for obj in self.not_support_rpm:
    #         assert isinstance(obj, BACnetObject)
    #
    #         self.__logger.debug(f'Polling not supporting PRM {obj} ...')
    #         try:
    #             values = self.simulate_rpm(obj=obj)
    #         except UnknownObjectError as e:
    #             self.__logger.error(f'{obj} is unknown: {e}')
    #         except Exception as e:
    #             self.__logger.error(f'{obj} polling error: {e}', exc_info=True)
    #         else:
    #             self.__logger.debug(f'From {obj} read: {values}. Sending to verifier ...')
    #             self.__put_data_into_verifier(properties=values)
    #
    #     # notify verifier, that device polled and should send collected objects via HTTP
    #     self.__logger.debug('All objects were polled. Send device_id to verifier')
    #     self.__put_device_end_to_verifier()

    async def write(
        self,
        value: int | float | str,
        obj: BACnetObj,
        wait: bool = False,
        **kwargs: Any,
    ) -> None:
        prop = kwargs["prop"]
        priority = kwargs["priority"]
        await self._gateway.async_add_job(self.write_property, value, obj, prop, priority)
        return None

    @log_exceptions(logger=_LOG)
    def write_property(
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
            f"{self._device_obj.property_list.interface[0]} "
            f"{camel_case(obj.object_type.name)} "
            f"{obj.object_id} "
            f"{camel_case(prop.name)} "
            f"{value} "
            f"- {priority}"
        )
        success = self.interface.client.write(args=args)
        self._LOG.debug(
            "Write property",
            extra={"device_id": self.id, "object": obj, "value": value, "success": success},
        )
        return success

    async def _wait_read_property(
        self,
        obj: BACnetObj,
        prop: ObjProperty,
        wait: bool = False,
    ) -> BACnetObj:
        """Waits for read property. Used to provide priority to write requests."""
        if wait:
            await self.interface.polling_event.wait()
        polled_obj = self.read_property(obj=obj, prop=prop)
        return polled_obj

    def read_property(self, obj: BACnetObj, prop: ObjProperty) -> BACnetObj:
        request = " ".join(
            (
                ":".join([str(item) for item in self._device_obj.property_list.interface]),
                camel_case(obj.object_type.name),
                str(obj.object_id),
                camel_case(prop.name),
            )
        )
        response = self.interface.client.read(request)
        self._LOG.debug(
            "Read property",
            extra={"device_id": self.id, "object": obj, "response": response},
        )
        if prop is ObjProperty.PRIORITY_ARRAY:
            response = self._decode_priority_array(priority_array=response)

        obj.set_property(value=response, prop=prop)
        return obj

    async def _wait_read_property_multiple(
        self, obj: BACnetObj, wait: bool = False
    ) -> BACnetObj:
        if wait:
            await self.interface.polling_event.wait()
        polled_obj = self.read_property_multiple(obj=obj, properties=obj.polling_properties)
        return polled_obj

    def read_property_multiple(
        self, obj: BACnetObj, properties: tuple[ObjProperty, ...]
    ) -> BACnetObj:
        request = " ".join(
            (
                ":".join([str(item) for item in self._device_obj.property_list.interface]),
                camel_case(obj.object_type.name),
                str(obj.object_id),
                *[prop.name for prop in properties],
            )
        )
        response = self.interface.client.readMultiple(request)
        self._LOG.debug(
            "Read property multiple",
            extra={"device_id": self.id, "object": obj, "response": response},
        )
        # Check values for None and empty strings
        values = {
            properties[i]: value
            for i, value in enumerate(response)
            if value is not None and str(value).strip()
        }
        for prop, val in values.items():
            if prop is ObjProperty.PRIORITY_ARRAY:
                val = self._decode_priority_array(priority_array=val)
            obj.set_property(value=val, prop=prop)
        return obj

    async def _wait_read_property_multiple_simulation(self, obj: BACnetObj) -> BACnetObj:
        """Simulates `read_property_multiple` with `read_property` by sending requests
        for each property separately. It works slowly. Used for devices not
        supported `read_property_multiple`.
        """
        for prop in obj.polling_properties:
            try:
                obj = await self._wait_read_property(obj=obj, prop=prop)
            except Exception as exc:  # pylint: disable=broad-except
                self._LOG.warning(
                    "Read error", extra={"object": obj, "property": prop, "exception": exc}
                )
        return obj

    async def read(self, obj: BACnetObj, wait: bool = False, **kwargs: Any) -> BACnetObj:
        if obj.segmentation_supported:
            try:
                polled_obj = await self._wait_read_property_multiple(obj=obj)
                return polled_obj
            except ReadPropertyMultipleException:
                obj.segmentation_supported = False
                _LOG.debug("Segmentation not supported", extra={"object": obj})

        polled_obj = await self._wait_read_property_multiple_simulation(obj=obj)
        return polled_obj

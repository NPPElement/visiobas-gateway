from __future__ import annotations

from typing import TYPE_CHECKING, Any

from BAC0.scripts.Lite import Lite  # type: ignore

from ...schemas import BACnetObj, DeviceObj, ObjProperty, TcpIpDevicePropertyList
from ...utils import camel_case, get_file_logger, get_subnet_interface, log_exceptions
from ..base_polling_device import BasePollingDevice
from ._bacnet_coder_mixin import BACnetCoderMixin

if TYPE_CHECKING:
    from visiobas_gateway.gateway import Gateway
else:
    Gateway = "Gateway"

_LOG = get_file_logger(name=__name__)


class BACnetDevice(BasePollingDevice, BACnetCoderMixin):
    """Implementation of BACnet device client."""

    def __init__(self, device_obj: DeviceObj, gateway: Gateway):
        super().__init__(device_obj, gateway)

        self.support_rpm: set[BACnetObj] = set()
        self.not_support_rpm: set[BACnetObj] = set()

        # self.__objects_per_rpm = 25
        # todo: Should we use one RPM for several objects?
        # todo: use COV subscribe

    @staticmethod
    def interface_name(device_obj: DeviceObj) -> str | None:
        assert isinstance(device_obj.property_list, TcpIpDevicePropertyList)

        ip_address = device_obj.property_list.address
        interface = get_subnet_interface(ip=ip_address)

        if interface:
            return str(interface)
        return None

    @property
    def is_client_connected(self) -> bool:
        return bool(self.interface.client)

    @log_exceptions(logger=_LOG)
    async def create_client(self, device_obj: DeviceObj) -> Lite:
        """Initializes BAC0 client."""
        assert isinstance(device_obj.property_list, TcpIpDevicePropertyList)

        interface = self.interface_name(device_obj=device_obj)
        if not interface:
            raise ConnectionError("No interface in same subnet.")
        self._LOG.debug(
            "Creating BAC0 client",
            extra={"device_id": self.id, "interface": interface},
        )
        client = Lite(ip=interface, port=device_obj.property_list.port)
        return client

    async def connect_client(self, client: Any) -> bool:
        if isinstance(client, Lite):
            return True
        return False

    async def _disconnect_client(self, client: Lite) -> None:
        client.disconnect()

    # async def _poll_objects(self, objs: Collection[BACnetObj]) -> None:
    #     for obj in objs:
    #         if obj.existing:
    #             await self.simulate_rpm(obj=obj)

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
        prop = kwargs.get("prop")
        priority = kwargs.get("priority")
        await self._gtw.async_add_job(self.write_property, value, obj, prop, priority)
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
        assert isinstance(self._device_obj.property_list, TcpIpDevicePropertyList)

        if self._is_binary_obj(obj=obj) and prop is ObjProperty.PRESENT_VALUE:
            value = self._encode_binary_present_value(value=value)  # type: ignore

        args = (
            f"{self._device_obj.property_list.interface} "
            f"{camel_case(obj.object_type.name)} "
            f"{obj.object_id} "
            f"{camel_case(prop.name)} "
            f"{value} "
            f"- {priority}"
        )
        success = self.interface.client.write(args=args)
        self._LOG.debug(
            "Write",
            extra={"device_id": self.id, "object": obj, "value": value, "success": success},
        )
        return success

    async def _read(
        self,
        obj: BACnetObj,
        prop: ObjProperty,
        wait: bool = False,
    ) -> BACnetObj:
        # prop = kwargs.get("prop")
        if not isinstance(prop, ObjProperty):
            raise ValueError(f"`prop` must be `ObjProperty` instance. Got {type(prop)}")

        if wait:
            await self.interface.polling_event.wait()
        polled_obj = self.read_property(obj=obj, prop=prop)
        return polled_obj
        # return await self._gtw.async_add_job(self.read_property, obj, prop)

    # @log_exceptions
    def read_property(self, obj: BACnetObj, prop: ObjProperty) -> BACnetObj:
        assert isinstance(self._device_obj.property_list, TcpIpDevicePropertyList)

        request = " ".join(
            (
                ":".join([str(item) for item in self._device_obj.property_list.interface]),
                camel_case(obj.object_type.name),
                str(obj.object_id),
                camel_case(prop.name),
            )
        )
        response = self.interface.client.read(request)

        if prop is ObjProperty.PRIORITY_ARRAY:
            response = self._decode_priority_array(priority_array=response)

        self._LOG.debug(
            "Read", extra={"device_id": self.id, "object": obj, "response": response}
        )
        obj.set_property(value=response, prop=prop)
        return obj

    # def read_property_multiple(self, obj: BACnetObj,
    #                            properties: tuple[ObjProperty]) -> dict:
    #     try:
    #         request = ' '.join([
    #             self.address,
    #             obj.type.name,
    #             str(obj.id),
    #             *[prop.name for prop in properties]
    #         ])
    #         response = self._client.readMultiple(request)
    #
    #         # check values for None and empty strings
    #         values = {properties[i]: value for i, value in enumerate(response)
    #                   if value is not None and str(value).strip()}
    #         for prop, val in values.items():
    #
    #
    #     except Exception as e:
    #         self._LOG.exception('Unhandled ReadPropertyMultiple error',
    #                             extra={'device_id': self.id, 'object_id': obj.id,
    #                                    'object_type': obj.type, 'exc': e, })
    #     # else:
    #     #     if values is not None:
    #     #         return values
    #     #     else:
    #     #         raise ReadPropertyMultipleException('Response is None')

    async def simulate_rpm(self, obj: BACnetObj) -> BACnetObj:
        for prop in obj.polling_properties:
            try:
                obj = await self._read(obj=obj, prop=prop)
            except Exception as exc:  # pylint: disable=broad-except
                self._LOG.warning(
                    "Read error", extra={"object": obj, "property": prop, "exception": exc}
                )
        return obj

    async def read(self, obj: BACnetObj, wait: bool = False, **kwargs: Any) -> BACnetObj:
        if wait:
            await self.interface.polling_event.wait()
        # if obj.segmentation_supported:# todo: implement RPM or RP
        polled_obj = await self.simulate_rpm(obj=obj)
        return polled_obj

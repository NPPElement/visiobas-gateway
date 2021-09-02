from typing import Any, Collection, Optional, Union

from BAC0.scripts.Lite import Lite  # type: ignore

from ..models import BACnetDeviceObj, BACnetObj, ObjProperty
from ..utils import log_exceptions
from .base_polling_device import BasePollingDevice

# Aliases
VisioBASGateway = Any  # ...gateway_loop


class BACnetDevice(BasePollingDevice):
    """Implementation of BACnet device client."""

    client: Lite = None  # todo

    def __init__(self, device_obj: BACnetDeviceObj, gateway: VisioBASGateway):
        super().__init__(device_obj, gateway)

        self.support_rpm: set[BACnetObj] = set()
        self.not_support_rpm: set[BACnetObj] = set()
        # self._client: BAC0.scripts.Lite = gateway.bacnet

        # self.__objects_per_rpm = 25
        # todo: Should we use one RPM for several objects?

    @property
    def address_port(self) -> str:
        return ":".join((str(self.address), str(self.port)))

    @property
    def is_client_connected(self) -> bool:
        return self.__class__.client is not None

    @log_exceptions
    def create_client(self) -> None:
        """Initializes BAC0 client."""
        if not self.is_client_connected:
            self._LOG.debug("Creating BAC0 client", extra={"device_id": self.device_id})
            self.__class__.client = Lite()  # todo params
        else:
            self._LOG.debug(
                "BAC0 client already created", extra={"device_id": self.device_id}
            )

    def close_client(self) -> None:
        pass
        # self._client.disconnect() # todo: add check for client usage by other devices

    async def _poll_objects(self, objs: Collection[BACnetObj]) -> None:
        # def _sync_poll_objects(objs_: Collection[BACnetObj]) -> None:
        #     for obj in objs_:
        #         await self.simulate_rpm(obj=obj)
        #
        # await self._gateway.async_add_job(_sync_poll_objects, objs)
        for obj in objs:
            await self.simulate_rpm(obj=obj)

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
        value: Union[int, float],
        obj: BACnetObj,
        wait: bool = False,
        # prop: ObjProperty, priority: Optional[int]
        **kwargs: Any,
    ) -> None:
        prop = kwargs.get("prop")
        priority = kwargs.get("priority")
        await self._gtw.async_add_job(self.write_property, value, obj, prop, priority)
        return None

    def write_property(
        self, value: Union[int, float], obj: BACnetObj, prop: ObjProperty, priority: int
    ) -> Optional[bool]:
        """Writes value to property value in object.

        Args:
            value: Value to write.
            obj: Object instance.
            prop: Property which write.
            priority: Value priority.

        Returns:
            Write is successful.
        """
        # priority = priority or self._gateway.api.priority
        args = "{0} {1} {2} {3} {4} - {5}".format(
            self.address_port, obj.type.name_, obj.id, prop.name, value, priority
        )
        is_successful = self.__class__.client.write(args=args)
        self._LOG.debug(
            "Write",
            extra={
                "device_id": self.device_id,
                "object_id": obj.id,
                "object_type": obj.type,
                "value": value,
                "success": is_successful,
            },
        )
        return is_successful

    async def read(
        self,
        obj: BACnetObj,
        wait: bool = False,
        # prop: ObjProperty
        **kwargs: Any,
    ) -> Any:
        prop = kwargs.get("prop")

        if wait:
            await self._polling.wait()
        return await self._gtw.async_add_job(self.read_property, obj, prop)

    def read_property(self, obj: BACnetObj, prop: ObjProperty) -> None:
        request = " ".join([self.address_port, obj.type.name_, str(obj.id), prop.name])
        response = self.__class__.client.read(request)
        self._LOG.debug(
            "Read",
            extra={
                "device_id": self.device_id,
                "object_id": obj.id,
                "object_type": obj.type,
                "response": response,
            },
        )
        try:
            obj.set_property_value(value=response, prop=prop)
        except AttributeError as exc:
            raise NotImplementedError(f"Property {prop} not found") from exc

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

    async def simulate_rpm(self, obj: BACnetObj) -> None:
        for prop in obj.type.properties:
            await self.read(obj=obj, prop=prop)

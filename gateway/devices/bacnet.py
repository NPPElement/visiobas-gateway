from typing import Any, Collection, Union, Optional

from BAC0.core.io.IOExceptions import (ReadPropertyException,
                                       NoResponseFromController,
                                       UnknownObjectError,
                                       UnknownPropertyError,
                                       NetworkInterfaceException, InitializationError)
from BAC0.scripts.Lite import Lite
from bacpypes.basetypes import PriorityArray

from .base_device import BaseDevice
from ..models import (ObjProperty, BACnetDeviceObj, BACnetObj, StatusFlags)

# Aliases
VisioBASGateway = Any  # ...gateway_loop


class BACnetDevice(BaseDevice):
    _client: Lite = None  # todo

    def __init__(self, device_obj: BACnetDeviceObj, gateway: VisioBASGateway):
        super().__init__(device_obj, gateway)

        self.support_rpm: set[BACnetObj] = set()
        self.not_support_rpm: set[BACnetObj] = set()
        # self._client: BAC0.scripts.Lite = gateway.bacnet

        # self.__objects_per_rpm = 25
        # todo: Should we use one RPM for several objects?

    @property
    def address_port(self) -> str:
        return ':'.join((str(self.address), str(self.port)))

    @property
    def is_client_connected(self) -> bool:
        return self.__class__._client is not None

    def create_client(self) -> None:
        """Initializes BAC0 client."""
        try:
            if not self.is_client_connected:
                self._LOG.debug('Creating BAC0 client', extra={'device_id': self.id})
                self.__class__._client = Lite()  # todo params
            else:
                self._LOG.debug('BAC0 client already created',
                                extra={'device_id': self.id})

        except (InitializationError, NetworkInterfaceException,
                Exception) as e:
            self._LOG.debug('Cannot create client',
                            extra={'device_id': self.id, 'exc': e, })

    def close_client(self) -> None:
        self._client.disconnect()

    async def _poll_objects(self, objs: Collection[BACnetObj]) -> None:
        def _sync_poll_objects(objs_: Collection[BACnetObj]) -> None:
            for obj in objs_:
                self.simulate_rpm(obj=obj)

        await self._gateway.async_add_job(_sync_poll_objects, objs)

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

    async def async_write_property(self, value: Union[int, float], obj: BACnetObj,
                                   prop: ObjProperty, priority: Optional[int]) -> bool:
        return await self._gateway.async_add_job(
            self.write_property, value, obj, prop, priority)

    def write_property(self, value: Union[int, float], obj: BACnetObj,
                       prop: ObjProperty, priority: Optional[int] = None) -> bool:
        """Writes value to property value in object.

        Args:
            value: Value to write.
            obj: Object instance.
            prop: Property which write.
            priority: Value priority.

        Returns:
            Write is successful.
        """
        priority = priority or self._gateway.api_priority
        try:
            args = '{0} {1} {2} {3} {4} - {5}'.format(self.address_port,
                                                      obj.type.name,
                                                      obj.id,
                                                      prop.name,
                                                      value,
                                                      priority
                                                      )
            is_successful = self.__class__._client.write(args=args)
            self._LOG.debug('Write',
                            extra={'device_id': self.id, 'object_id': obj.id,
                                   'object_type': obj.type, 'value': value,
                                   'success': is_successful, })
            return is_successful
        except (ValueError, Exception) as e:
            self._LOG.exception('Unhandled WriteProperty error',
                                extra={'device_id': self.id, 'object_id': obj.id,
                                       'object_type': obj.type, 'exc': e, 'value': value})

    async def async_read_property(self, obj: BACnetObj,
                                  prop: ObjProperty) -> Any:
        return await self._gateway.async_add_job(self.read_property, obj, prop)

    def read_property(self, obj: BACnetObj, prop: ObjProperty) -> Any:
        try:
            request = ' '.join([
                self.address_port,
                obj.type.name,
                str(obj.id),
                prop.name
            ])
            response = self.__class__._client.read(request)
            self._LOG.debug('Read',
                            extra={'device_id': self.id, 'object_id': obj.id,
                                   'object_type': obj.type, 'response': response, })
            if prop is ObjProperty.presentValue:
                obj.set_pv(value=response)
            elif prop is ObjProperty.statusFlags:
                obj.sf = StatusFlags(flags=response)
            elif prop is ObjProperty.priorityArray:
                obj.pa = self._pa_to_tuple(pa=response)
                self._LOG.debug('priority array extracted', extra={'priority_array': obj.pa,
                                                                   'object_id': obj.id,
                                                                   'object_type': obj.type,
                                                                   'device_id': self.id, })
            # todo

        except (UnknownPropertyError, UnknownObjectError,
                NoResponseFromController, ReadPropertyException) as e:
            obj.exception = e
            self._LOG.warning('ReadProperty error',
                              extra={'device_id': self.id, 'object_id': obj.id,
                                     'object_type': obj.type, 'exc': e, })
        except Exception as e:
            obj.exception = e
            self._LOG.exception(f'Unexpected read error: {e}',
                                extra={'device_id': self.id, 'object_id': obj.id,
                                       'object_type': obj.type, 'exc': e, })
        else:
            return response

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

    def simulate_rpm(self, obj: BACnetObj) -> None:
        for prop in obj.type.properties:
            self.read_property(obj=obj, prop=prop)

    @staticmethod
    def _pa_to_tuple(pa: PriorityArray) -> tuple:
        """Represent `bacpypes` object `PriorityArray` as tuple."""
        priorities = [v[0] if k[0] != 'null' else None
                      for k, v in [zip(*pa.value[i].dict_contents().items())
                                   for i in range(1, pa.value[0] + 1)
                                   ]
                      ]

        return tuple(priorities)

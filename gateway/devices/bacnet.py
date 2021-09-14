import asyncio
from typing import Any, Collection, Union

from BAC0.core.io.IOExceptions import (ReadPropertyException, NoResponseFromController,
                                       UnknownObjectError, UnknownPropertyError,
                                       NetworkInterfaceException, InitializationError)
from BAC0.scripts.Lite import Lite
from bacpypes.basetypes import PriorityArray

from .base_polling_device import BasePollingDevice
from ..models import (ObjProperty, BACnetDeviceObj, BACnetObj, StatusFlags)
from ipaddress import IPv4Interface
from ..utils.network import get_subnet_interface

# Aliases
VisioBASGateway = Any  # ...gateway_loop


class BACnetDevice(BasePollingDevice):
    _clients: dict[IPv4Interface, Lite] = {}
    _locks: dict[IPv4Interface, asyncio.Lock] = {}


    def __init__(self, device_obj: BACnetDeviceObj, gateway: VisioBASGateway):
        super().__init__(device_obj, gateway)

        self.support_rpm: set[BACnetObj] = set()
        self.not_support_rpm: set[BACnetObj] = set()
        self.interface: IPv4Interface = None
        # self._client: BAC0.scripts.Lite = gateway.bacnet

        # self.__objects_per_rpm = 25
        # todo: Should we use one RPM for several objects?

    @property
    def address_port(self) -> str:
        return ':'.join((str(self.address), str(self.port)))

    @property
    def is_client_connected(self) -> bool:
        return isinstance(self.__class__._clients.get(self.interface), Lite)

    @property
    def _lock(self) -> asyncio.Lock:
        interface_lock = self.__class__._locks.get(self.interface, asyncio.Lock())
        self.__class__._locks[self.interface] = interface_lock
        return interface_lock

    async def create_client(self) -> None:
        """Initializes BAC0 client."""
        try:
            device_ip_address = self._dev_obj.property_list.address
            self.interface = get_subnet_interface(ip=device_ip_address)
            if not isinstance(self.interface, IPv4Interface):
                raise ValueError(f'No interface to interact with {device_ip_address} found')

            self._lock  # Init lock.

            if self.interface in self.__class__._clients:
                self._LOG.debug(
                    f'BAC0 client for interface {self.interface} already exists',
                    extra={'device_id': self.id})
                return None

            self._LOG.debug('Creating BAC0 client', extra={'device_id': self.id})
            client = Lite(ip=self.interface.with_prefixlen)
            self.__class__._clients[self.interface] = client

        except (InitializationError, NetworkInterfaceException,
                Exception) as e:
            self._LOG.debug('Cannot create client',
                            extra={'device_id': self.id, 'exc': e, })


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
        self._LOG.debug('_poll_objects completed')

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

    async def write(self, value: Union[int, float], obj: BACnetObj,
                    # prop: ObjProperty, priority: Optional[int]
                    **kwargs) -> bool:
        prop = kwargs.get('prop')
        priority = kwargs.get('priority')
        async with self._lock:
            return await self._gtw.async_add_job(
                self.write_property, value, obj, prop, priority)

    def write_property(self, value: Union[int, float], obj: BACnetObj,
                       prop: ObjProperty, priority: int) -> bool:
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
        try:
            args = '{0} {1} {2} {3} {4} - {5}'.format(self.address_port,
                                                      obj.type.name, obj.id,
                                                      prop.name, value, priority)
            is_successful = self.__class__._clients[self.interface].write(args=args)
            self._LOG.debug('Write', extra={'device_id': self.id, 'object_id': obj.id,
                                            'object_type': obj.type, 'value': value,
                                            'success': is_successful, })
            return is_successful
        except (ValueError, Exception) as e:
            self._LOG.exception('Unhandled WriteProperty error',
                                extra={'device_id': self.id, 'object_id': obj.id,
                                       'object_type': obj.type, 'exc': e, 'value': value})

    async def read(self, obj: BACnetObj,
                   # prop: ObjProperty
                   **kwargs) -> Any:
        prop = kwargs.get('prop')

        if kwargs.get('wait', True):
            await self._polling.wait()
        async with self._lock:
            return await self._gtw.async_add_job(self.read_property, obj, prop)

    def read_property(self, obj: BACnetObj, prop: ObjProperty) -> Any:
        try:
            request = ' '.join([
                self.address_port, obj.type.name, str(obj.id), prop.name
            ])
            response = self.__class__._clients[self.interface].read(request)
            self._LOG.debug('Read',
                            extra={'device_id': self.id, 'object_id': obj.id,
                                   'object_type': obj.type, 'response': response, })
            # TODO: refactor set_property()
            if prop is ObjProperty.presentValue:
                obj.set_pv(value=response)
            elif prop is ObjProperty.statusFlags:
                obj.sf = StatusFlags(flags=response)
            elif prop is ObjProperty.reliability:
                obj.reliability = response
            elif prop is ObjProperty.priorityArray:
                obj.pa = self._pa_to_tuple(pa=response)
                self._LOG.debug('Priority array extracted',
                                extra={'priority_array': obj.pa, 'object_id': obj.id,
                                       'object_type': obj.type, 'device_id': self.id, })
            else:
                NotImplementedError('Other properties not support now.')

        except (UnknownPropertyError, UnknownObjectError,
                NoResponseFromController, ReadPropertyException,
                Exception) as e:
            if prop is ObjProperty.presentValue:
                obj.set_exc(exc=e)
            self._LOG.warning('ReadProperty error',
                              extra={'device_id': self.id, 'object_id': obj.id,
                                     'object_type': obj.type, 'exc': e,
                                     'property': prop,
                                     'unreachable_in_row': obj.unreachable_in_row, })
        # except Exception as e:
        #     obj.exception = e
        #     self._LOG.exception(f'Unexpected read error: {e}',
        #                         extra={'device_id': self.id, 'object_id': obj.id,
        #                                'object_type': obj.type, 'exc': e, })
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

    async def simulate_rpm(self, obj: BACnetObj) -> None:
        for prop in obj.type.properties:
            await self.read(obj=obj, prop=prop)

    @staticmethod
    def _pa_to_tuple(pa: PriorityArray) -> tuple:
        """Represent `bacpypes` object `PriorityArray` as tuple."""
        priorities = [v[0] if k[0] != 'null' else None
                      for k, v in [zip(*pa.value[i].dict_contents().items())
                                   for i in range(1, pa.value[0] + 1)
                                   ]
                      ]

        return tuple(priorities)

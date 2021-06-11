from typing import Any, Collection

from BAC0 import lite
from BAC0.core.io.IOExceptions import (ReadPropertyException,
                                       NoResponseFromController,
                                       UnknownObjectError,
                                       UnknownPropertyError,
                                       ReadPropertyMultipleException,
                                       NetworkInterfaceException, InitializationError)
from BAC0.scripts.Lite import Lite

from .base_device import BaseDevice
from ..models import (ObjProperty, BACnetDeviceObj, BACnetObj, StatusFlags)

# Aliases
VisioBASGateway = Any  # ...gateway_loop


class BACnetDevice(BaseDevice):
    _client: Lite = None

    def __init__(self, device_obj: BACnetDeviceObj, gateway: VisioBASGateway):
        super().__init__(device_obj, gateway)
        # self._client: Lite = None

        self.support_rpm: set[BACnetObj] = set()
        self.not_support_rpm: set[BACnetObj] = set()

        # self.__objects_per_rpm = 25
        # todo: Should we use one RPM for several objects?

    @property
    def is_client_connected(self) -> bool:
        return bool(self._client)

    def create_client(self) -> None:
        """Initializes BAC0 client."""
        self._LOG.debug('Creating BAC0 client', extra={'device_id': self.id})
        try:
            if not self._client:
                self._client = lite()

        except (InitializationError, NetworkInterfaceException,
                Exception) as e:
            self._LOG.debug('Cannot create client',
                            extra={'device_id': self.id, 'exc': e, })
        else:
            self._LOG.debug('Client created', extra={'device_id': self.id})

    async def _poll_objects(self, objs: Collection[BACnetObj]) -> None:
        raise NotImplementedError

    def poll(self) -> None:
        """ Poll all object from device.
            Send each object into verifier after answer.
            When all objects polled, send device_id into verifier as finish signal
        """
        for obj in self.support_rpm:
            assert isinstance(obj, BACnetObject)

            self.__logger.debug(f'Polling supporting PRM {obj} ...')
            try:
                values = self.rpm(obj=obj)
                self.__logger.debug(f'{obj} values: {values}')
            except ReadPropertyMultipleException as e:
                self.__logger.warning(f'{obj} rpm error: {e}\n'
                                      f'{obj} Marking as not supporting RPM ...')
                self.not_support_rpm.add(obj)
                # self.support_rpm.discard(obj)

            except Exception as e:
                self.__logger.error(f'{obj} polling error: {e}', exc_info=True)
            else:
                self.__logger.debug(f'From {obj} read: {values}. Sending to verifier ...')
                self.__put_data_into_verifier(properties=values)

        self.support_rpm.difference_update(self.not_support_rpm)

        for obj in self.not_support_rpm:
            assert isinstance(obj, BACnetObject)

            self.__logger.debug(f'Polling not supporting PRM {obj} ...')
            try:
                values = self.simulate_rpm(obj=obj)
            except UnknownObjectError as e:
                self.__logger.error(f'{obj} is unknown: {e}')
            except Exception as e:
                self.__logger.error(f'{obj} polling error: {e}', exc_info=True)
            else:
                self.__logger.debug(f'From {obj} read: {values}. Sending to verifier ...')
                self.__put_data_into_verifier(properties=values)

        # notify verifier, that device polled and should send collected objects via HTTP
        self.__logger.debug('All objects were polled. Send device_id to verifier')
        self.__put_device_end_to_verifier()

    def read_property(self, obj: BACnetObj, prop: ObjProperty) -> Any:
        try:
            request = ' '.join([
                self.address,
                obj.type.name,
                str(obj.id),
                prop.name
            ])
            response = self._client.read(request)
            if prop is ObjProperty.presentValue:
                obj.set_pv(value=response)
            elif prop is ObjProperty.statusFlags:
                obj.sf = StatusFlags(flags=response)
            # todo

        except (UnknownPropertyError, UnknownObjectError, NoResponseFromController,
                ReadPropertyException) as e:
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

    def read_property_multiple(self, obj: BACnetObj,
                               properties: tuple[ObjProperty]) -> dict:
        try:
            request = ' '.join([
                self.address,
                obj.type.name,
                str(obj.id),
                *[prop.name for prop in properties]
            ])
            response = self._client.readMultiple(request)

            # check values for None and empty strings
            values = {properties[i]: value for i, value in enumerate(response)
                      if value is not None and str(value).strip()}
            for prop, val in values.items():
                

        except Exception as e:
            self._LOG.exception('Unhandled ReadPropertyMultiple error',
                                extra={'device_id': self.id, 'object_id': obj.id,
                                       'object_type': obj.type, 'exc': e, })
        # else:
        #     if values is not None:
        #         return values
        #     else:
        #         raise ReadPropertyMultipleException('Response is None')

    def __simulate_rpm(self, obj: BACnetObj, properties: list[ObjProperty]) -> dict:
        values = {}
        for prop in properties:
            try:
                response = self.read_property(obj=obj, prop=prop)

            except (UnknownObjectError, NoResponseFromController) as e:
                self.__logger.warning(f'sRPM Error: {e}')
                raise e

            except (UnknownPropertyError, ReadPropertyException) as e:
                if prop is ObjProperty.priorityArray:
                    continue
                self.__logger.warning(f'sRPM Error: {e}')
                raise e
            except TypeError as e:
                self.__logger.error(f'Type error: {e}')
                raise e
            except Exception as e:
                self.__logger.error(f'sRPM error: {e}', exc_info=True)

            else:
                values.update({prop: response})
                # self.not_support_rpm.update(obj)

        return values

    def rpm(self, obj: BACnetObject) -> dict:
        properties = {
            ObjProperty.deviceId: self.id,
            ObjProperty.objectName: obj.name,
            ObjProperty.objectType: obj.type,
            ObjProperty.objectIdentifier: obj.id,
        }
        try:
            values = self.read_property_multiple(obj=obj,
                                                 properties=obj.type.properties
                                                 )

        except ReadPropertyMultipleException as e:
            self.__logger.error(f'Read Error: {e}')
            raise e
        else:
            properties.update(values)
            return properties

    def simulate_rpm(self, obj: BACnetObject) -> dict:
        properties = {
            ObjProperty.deviceId: self.id,
            ObjProperty.objectName: obj.name,
            ObjProperty.objectType: obj.type,
            ObjProperty.objectIdentifier: obj.id,
        }

        try:
            values = self.__simulate_rpm(obj=obj,
                                         properties=obj.type.properties
                                         )

        except NoResponseFromController as e:
            self.__logger.error(f'No response error: {e}')
            values = get_fault_obj_properties(reliability='no-response')
        except UnknownPropertyError as e:
            self.__logger.error(f'Unknown property error: {e}')
            values = get_fault_obj_properties(reliability='unknown-property')
        except UnknownObjectError as e:
            self.__logger.error(f'Unknown object error: {e}')
            values = get_fault_obj_properties(reliability='unknown-object')
        except (ReadPropertyException, TypeError) as e:
            self.__logger.error(f'RP error: {e}')
            values = get_fault_obj_properties(reliability='rp-error')
        except Exception as e:
            self.__logger.error(f'Read Error: {e}', exc_info=True)
            values = get_fault_obj_properties(reliability='error')
        finally:
            properties.update(values)
            return properties

    def __put_device_end_to_verifier(self) -> None:
        """ device_id in queue means that device polled.
            Should send collected objects to HTTP
        """
        self.__verifier_queue.put(self.id)

    def __put_data_into_verifier(self, properties: dict) -> None:
        """ Send collected data about obj into BACnetVerifier
        """
        self.__verifier_queue.put(properties)

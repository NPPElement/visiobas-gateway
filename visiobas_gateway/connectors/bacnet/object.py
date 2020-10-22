import logging

from BAC0.core.io.IOExceptions import ReadPropertyMultipleException, \
    NoResponseFromController, UnknownObjectError, ReadPropertyException, Timeout, APDUError

from visiobas_gateway.connectors.bacnet.object_property import ObjectProperty
from visiobas_gateway.connectors.bacnet.object_type import ObjectType
from visiobas_gateway.connectors.bacnet.status_flags import StatusFlags


class Object:
    def __init__(self, device, type_: ObjectType, id_: int):
        self.__device = device

        self.__bacnet_properties = {
            ObjectProperty.objectType: type_,
            ObjectProperty.objectIdentifier: id_
        }

        self.__logger = self.__logger = logging.getLogger(f'{self}')

        self.__not_support_rpm: bool = False
        self.__not_responding: bool = False
        self.__unknown_object: bool = False

    @property
    def __type(self) -> ObjectType:
        return self.__bacnet_properties[ObjectProperty.objectType]

    @property
    def __id(self) -> int:
        return self.__bacnet_properties[ObjectProperty.objectIdentifier]

    def __repr__(self):
        return f'{self.__device} ({self.__type}, {self.__id})'

    def is_responding(self) -> bool:
        return not self.__not_responding

    def is_support_rpm(self) -> bool:
        return not self.__not_support_rpm

    def is_unknown(self):
        return self.__unknown_object

    def mark(self,
             *,
             not_support_rpm: bool = None,
             not_responding: bool = None,
             unknown_object: bool = None
             ) -> None:
        if not_support_rpm is not None:
            self.__not_support_rpm = not_support_rpm
            self.__logger.debug(f'{self} marked as not supporting RPM')
        if not_responding:
            self.__not_responding = not_responding
            self.__logger.debug(f'{self} marked as not responding')
        if unknown_object:
            self.__unknown_object = unknown_object
            self.__logger.debug(f'{self} marked as unknown object')

    def __read_property(self, property_: ObjectProperty):
        try:
            request = ' '.join([
                self.__device.address,
                self.__bacnet_properties[ObjectProperty.objectType].name,
                str(self.__bacnet_properties[ObjectProperty.objectIdentifier]),
                property_.name
            ])
            value = self.__device.network.read(request)
        except UnknownObjectError as e:
            raise ReadPropertyException(f'Unknown object: {e}')
        except NoResponseFromController as e:
            raise ReadPropertyException(f'No response from controller: {e}')
        except KeyError as e:
            raise ReadPropertyException(f'Unknown property {property_}. {e}')
        except Timeout as e:
            raise ReadPropertyException(f'Timeout: {e}')
        except Exception as e:
            self.__logger.error(f'RP Error: {e}', exc_info=True)
            raise ReadPropertyException(f'RP Error: {e}')
        else:
            # self.__bacnet_properties[property_] = value
            return value

    def __read_property_multiple(self, properties: list) -> dict:
        try:
            request = ' '.join([
                self.__device.address,
                self.__bacnet_properties[ObjectProperty.objectType].name,
                str(self.__bacnet_properties[ObjectProperty.objectIdentifier]),
                *[prop.name for prop in properties]
            ])
            response = self.__device.network.readMultiple(request, prop_id_required=True)

            values = {}
            for each in response:
                value, property_id = each
                property_ = ObjectProperty(value=property_id)
                values.update({property_: value})
                # self.__bacnet_properties.update({property_: value})
        except ValueError as e:
            raise ReadPropertyMultipleException(f'RPM Error: {e}')
        except Exception as e:
            raise ReadPropertyMultipleException(f'RPM Error: {e}')
        else:
            return values

    def __simulate_rpm(self, properties: list):

        values = {}
        for property_ in properties:
            try:
                value = self.__read_property(property_=property_)
                values.update({property_: value})
            except ReadPropertyException:
                self.mark(not_responding=True)
            except APDUError:
                self.mark(not_responding=True)
            except Timeout:
                self.mark(not_responding=True)  # todo: What we should doing with timeout?
            except NoResponseFromController:
                self.mark(not_responding=True)
            except UnknownObjectError:
                self.mark(unknown_object=True)
            except Exception as e:
                self.__logger.error(f'RPM Simulation Error: {e}', exc_info=True)
                raise Exception(f'RPM Simulation  Error: {e}', )
            else:
                self.mark(not_support_rpm=True)
        return values

    def read(self, properties: list) -> dict:
        if self.is_responding() and not self.is_unknown():
            if self.is_support_rpm():
                try:
                    values = self.__read_property_multiple(properties=properties)
                except ReadPropertyMultipleException:
                    try:
                        values = self.__simulate_rpm(properties=properties)
                    except Exception as e:
                        self.__logger.error(f'Read Error: {e}', exc_info=True)
                        return {}
            else:
                try:
                    values = self.__simulate_rpm(properties=properties)
                except Exception as e:
                    self.__logger.error(f'Read Error: {e}', exc_info=True)
                    return {}

            return values

    def evaluate(self, values: dict) -> dict:
        # todo replace to verifier
        #   temp

        bacnet_properties = {}
        if not values:
            return bacnet_properties

        sf = values.get(ObjectProperty.statusFlags, [0, 0, 0, 0])
        if sf:
            bacnet_properties.update({ObjectProperty.statusFlags: StatusFlags(sf)})
        else:
            bacnet_properties.update({ObjectProperty.statusFlags: StatusFlags()})

        pv = values.get(ObjectProperty.presentValue, 'null')
        if pv and pv != 'null':
            if pv == 'active':
                pv = 1
            elif pv == 'inactive':
                pv = 0
            bacnet_properties.update({ObjectProperty.presentValue: pv})
        else:
            status_flags = values.get(ObjectProperty.statusFlags, [0, 0, 0, 0])
            status_flags = StatusFlags(status_flags=status_flags)
            status_flags.set(fault=True)
            bacnet_properties.update({
                ObjectProperty.presentValue: 'null',
                ObjectProperty.statusFlags: status_flags
            })

        # todo: make reliability Enum
        # todo: implement reliability concatenation
        if not self.is_responding():
            status_flags = bacnet_properties.get(ObjectProperty.statusFlags, StatusFlags())
            status_flags.set(fault=True)
            bacnet_properties.update({
                ObjectProperty.presentValue: 'null',
                ObjectProperty.statusFlags: status_flags,
                ObjectProperty.reliability: 'no-response'
            })

        elif self.is_unknown():
            status_flags = bacnet_properties.get(ObjectProperty.statusFlags, StatusFlags())
            status_flags.set(fault=True)
            bacnet_properties.update({
                ObjectProperty.presentValue: 'null',
                ObjectProperty.statusFlags: status_flags,
                ObjectProperty.reliability: 'unknown-object'
            })
        return bacnet_properties

    def as_str(self, properties: dict):
        return ' '.join([
            str(self.__id),
            str(self.__type.id),
            str(properties.get(ObjectProperty.presentValue, 'null')),
            str(properties.get(ObjectProperty.statusFlags, '0')),
            str(properties.get(ObjectProperty.reliability, ''))
        ]).strip()

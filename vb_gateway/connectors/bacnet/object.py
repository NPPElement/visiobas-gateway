import logging

from BAC0.core.io.IOExceptions import ReadPropertyMultipleException, \
    NoResponseFromController, UnknownObjectError, ReadPropertyException, Timeout

from vb_gateway.connectors.bacnet.object_property import ObjProperty
from vb_gateway.connectors.bacnet.object_type import ObjType


class BACnetObject:
    def __init__(self, device, type_: ObjType, id_: int, name: str = None):
        self.__device = device

        self.type = type_
        self.id = id_
        if name:
            self.name = name

        self.__logger = self.__logger = logging.getLogger(f'{self}')

        # todo move in device
        # TODO: MOVE READ METHODS INTO DEVICE
        self.__not_support_rpm: bool = False
        # self.__not_responding: bool = False
        self.is_unknown: bool = False

    def __repr__(self):
        return f'{self.__device} ({self.type}, {self.id})'

    def __hash__(self):
        return hash((self.type, self.id))

    # def is_responding(self) -> bool:
    #     return not self.__not_responding

    def is_support_rpm(self) -> bool:
        return not self.__not_support_rpm

    def mark(self,
             *,
             not_support_rpm: bool = None,
             not_responding: bool = None,
             unknown_object: bool = None
             ) -> None:
        if not_support_rpm is not None:
            self.__not_support_rpm = not_support_rpm
            self.__device.not_support_rpm.add(self)
            self.__logger.debug(f'{self} marked as not supporting RPM')
        # if not_responding:
        #     self.__not_responding = not_responding
        #     self.__device.not_responding.add(self)
        #     self.__logger.debug(f'{self} marked as not responding')
        if unknown_object:
            self.is_unknown = unknown_object
            self.__device.unknown_objects.add(self)
            self.__logger.debug(f'{self} marked as unknown object')

    def read_property(self, property_: ObjProperty):
        try:
            request = ' '.join([
                self.__device.address,
                self.type.name,
                str(self.id),
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
            self.__logger.error(f'RP Error: {e}')  # , exc_info=True)
            raise ReadPropertyException(f'RP Error: {e}')
        else:
            return value

    def __read_property_multiple(self, properties: list) -> dict:
        try:
            request = ' '.join([
                self.__device.address,
                self.type.name,
                str(self.id),
                *[prop.name for prop in properties]
            ])
            response = self.__device.network.readMultiple(request, prop_id_required=True)

            values = {}
            for each in response:
                value, property_id = each
                property_ = ObjProperty(value=property_id)
                values.update({property_: value})
        except ValueError as e:
            raise ReadPropertyMultipleException(f'RPM Error: {e}')
        except Exception as e:
            raise ReadPropertyMultipleException(f'RPM Error: {e}')
        else:
            return values

    def __simulate_rpm(self, properties: list) -> dict:

        values = {}
        for property_ in properties:
            try:
                value = self.read_property(property_=property_)
                values.update({property_: value})
            # except ReadPropertyException:
            #     self.mark(not_responding=True)
            # except APDUError:
            #     self.mark(not_responding=True)
            # except Timeout:
            #     self.mark(not_responding=True)  # todo: What we should doing with timeout?
            # except NoResponseFromController:
            #     self.mark(not_responding=True)
            except UnknownObjectError:
                self.mark(unknown_object=True)
            except ValueError as e:
                self.__logger.error(f'RPM Simulation Error: {e}')  # , exc_info=True)
                raise ReadPropertyException('RPM Simulation Error')
            except Exception as e:
                self.__logger.error(f'RPM Simulation Error: {e}')  # , exc_info=True)
                # raise Exception(f'RPM Simulation  Error: {e}', )
                raise ReadPropertyException('RPM Simulation Error')
            else:
                self.mark(not_support_rpm=True)
        return values

    def read(self, properties: list) -> dict or None:
        if self.is_support_rpm():
            try:
                values = self.__read_property_multiple(properties=properties)
            except ReadPropertyMultipleException:
                try:
                    values = self.__simulate_rpm(properties=properties)
                except Exception as e:
                    self.__logger.error(f'Read Error: {e}')  # , exc_info=True)
                    return {}
        else:
            try:
                values = self.__simulate_rpm(properties=properties)
            except Exception as e:
                self.__logger.error(f'Read Error: {e}')  # , exc_info=True)
                return {}

        return values

    # def evaluate(self, values: dict) -> dict:
    #     # todo replace to verifier
    #     #   temp
    #
    #     bacnet_properties = {}
    #     if not values:
    #         return bacnet_properties
    #
    #     sf = values.get(ObjProperty.statusFlags, [0, 0, 0, 0])
    #     # if sf:
    #     bacnet_properties.update({ObjProperty.statusFlags: StatusFlags(sf)})
    #     # else:
    #     #     bacnet_properties.update({ObjectProperty.statusFlags: StatusFlags()})
    #
    #     pv = values.get(ObjProperty.presentValue, 'null')
    #
    #     if pv != 'null' and pv != float('inf') and pv != float('-inf'):
    #         if pv == 'active':
    #             pv = 1
    #         elif pv == 'inactive':
    #             pv = 0
    #         bacnet_properties.update({ObjProperty.presentValue: pv})
    #
    #     elif pv == 'null':
    #         status_flags = values.get(ObjProperty.statusFlags, [0, 0, 0, 0])
    #         status_flags = StatusFlags(status_flags=status_flags)
    #         status_flags.set(fault=True)
    #         bacnet_properties.update({
    #             ObjProperty.presentValue: 'null',
    #             ObjProperty.statusFlags: status_flags,
    #             ObjProperty.reliability: '7'
    #         })
    #
    #     elif pv == float('inf'):
    #         status_flags = values.get(ObjProperty.statusFlags, [0, 0, 0, 0])
    #         status_flags = StatusFlags(status_flags=status_flags)
    #         status_flags.set(fault=True)
    #         bacnet_properties.update({
    #             ObjProperty.presentValue: 'null',
    #             ObjProperty.statusFlags: status_flags,
    #             ObjProperty.reliability: '2'
    #         })
    #     elif pv == float('-inf'):
    #         status_flags = values.get(ObjProperty.statusFlags, [0, 0, 0, 0])
    #         status_flags = StatusFlags(status_flags=status_flags)
    #         status_flags.set(fault=True)
    #         bacnet_properties.update({
    #             ObjProperty.presentValue: 'null',
    #             ObjProperty.statusFlags: status_flags,
    #             ObjProperty.reliability: '3'
    #         })
    #
    #     if ObjProperty.priorityArray in values:
    #         bacnet_properties.update({
    #             ObjProperty.priorityArray: values[ObjProperty.priorityArray]
    #         })
    #
    #     # todo: make reliability Enum
    #     # todo: implement reliability concatenation
    #     # if not self.is_responding():
    #     #     status_flags = bacnet_properties.get(ObjectProperty.statusFlags, StatusFlags())
    #     #     status_flags.set(fault=True)
    #     #     bacnet_properties.update({
    #     #         ObjectProperty.presentValue: 'null',
    #     #         ObjectProperty.statusFlags: status_flags,
    #     #         ObjectProperty.reliability: '64'
    #     #     })
    #
    #     if self.is_unknown():
    #         status_flags = bacnet_properties.get(ObjProperty.statusFlags, StatusFlags())
    #         status_flags.set(fault=True)
    #         bacnet_properties.update({
    #             ObjProperty.presentValue: 'null',
    #             ObjProperty.statusFlags: status_flags,
    #             ObjProperty.reliability: '65'
    #         })
    #     return bacnet_properties

    # @staticmethod
    # def __extract_priorities(priority_array: PriorityArray) -> str:
    #     """ Converts priorityArray object to str like ,,,,,,,,40.5,,,,,,49.2,
    #     """
    #     pa_size = priority_array.value[0]
    #     priorities = []
    #
    #     for i in range(1, pa_size + 1):
    #         pa = priority_array.value[i]
    #         key, value = zip(*pa.dict_contents().items())
    #         if key[0] == 'null':
    #             priorities.append('')
    #         else:
    #             priorities.append(value[0])
    #
    #     priorities = [str(pr) for pr in priorities]
    #     pa_str = ','.join(priorities)
    #     return pa_str
    #
    # def as_str(self, properties: dict) -> str:
    #     if ObjProperty.priorityArray in properties:
    #         return ' '.join([
    #             str(self.id),
    #             str(self.type.id),
    #             str(properties.get(ObjProperty.presentValue, 'null')),
    #             self.__extract_priorities(properties[ObjProperty.priorityArray]),
    #             str(properties.get(ObjProperty.statusFlags, '0')),
    #             str(properties.get(ObjProperty.reliability, ''))
    #         ]).strip()
    #     else:
    #         return ' '.join([
    #             str(self.id),
    #             str(self.type.id),
    #             str(properties.get(ObjProperty.presentValue, 'null')),
    #             str(properties.get(ObjProperty.statusFlags, '0')),
    #             str(properties.get(ObjProperty.reliability, ''))
    #         ]).strip()

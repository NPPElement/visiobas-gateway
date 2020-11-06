import logging

from BAC0.core.io.IOExceptions import ReadPropertyMultipleException, \
    NoResponseFromController, UnknownObjectError, ReadPropertyException, Timeout, \
    UnknownPropertyError

from vb_gateway.connectors.bacnet.object_property import ObjProperty
from vb_gateway.connectors.bacnet.object_type import ObjType


class BACnetObject(object):  # Should we inherit from object do deny __dict__?
    def __init__(self, device, type_: ObjType, id_: int, name: str = None):

        __slots__ = ('type', 'id', 'name', '__logger',
                     '__not_support_rpm', 'is_unknown')
        self.__device = device

        self.type = type_
        self.id = id_
        if name:
            self.name = name

        self.__logger = self.__logger = logging.getLogger(f'{self}')
        # base_path = Path(__file__).resolve().parent.parent.parent
        # log_path = base_path / f'logs/{self.__device.id}-objects.log'
        # handler = RotatingFileHandler(filename=log_path,
        #                               mode='a',
        #                               maxBytes=50_000_000,
        #                               backupCount=1,
        #                               encoding='utf-8'
        #                               )
        # LOGGER_FORMAT = '%(levelname)-8s [%(asctime)s] [%(threadName)s] %(name)s - (%(filename)s).%(funcName)s(%(lineno)d): %(message)s'
        # formatter = logging.Formatter(LOGGER_FORMAT)
        # handler.setFormatter(formatter)
        # self.__logger.addHandler(handler)

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
        except UnknownPropertyError as e:
            raise UnknownPropertyError(f'Unknown property: {property_} error')
        except UnknownObjectError as e:
            raise ReadPropertyException(f'Unknown object: {e}')
        except NoResponseFromController as e:
            raise ReadPropertyException(f'No response from controller: {e}')
        except KeyError as e:
            raise ReadPropertyException(f'Unknown property {property_}. {e}')
        except Timeout as e:
            raise ReadPropertyException(f'Timeout: {e}')
        except Exception as e:
            raise ReadPropertyException(f'RP Error: {e}')
        else:
            # self.__logger.debug(f'{self} RPM Success: {values}')  # , exc_info=True)
            return value

    def __read_property_multiple(self, properties: list) -> dict:
        request = ' '.join([
                self.__device.address,
                self.type.name,
                str(self.id),
                *[str(prop.id) for prop in properties]
            ])
        response = self.__device.network.readMultiple(request, prop_id_required=True)
        # FIXME

        values = {}
        for each in response:
            try:
                value, property_id = each
                property_ = ObjProperty(value=property_id)
            except UnknownPropertyError:
                continue
            except ValueError as e:
                self.__logger.error(f'RPM Error: {e}')  # , exc_info=True)
                raise ReadPropertyMultipleException(f'RPM Error: {e}')
            except Exception as e:
                self.__logger.error(f'RPM Error: {e}')  # , exc_info=True)
                raise ReadPropertyMultipleException(f'RPM Error: {e}')
            else:
                values.update({property_: value})
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
            except UnknownPropertyError as e:
                if property_ is ObjProperty.priorityArray:
                    continue
                raise ReadPropertyException(f'Unknown property error: {e}')

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

        self.__logger.debug(f'{self} read: {values}')
        return values

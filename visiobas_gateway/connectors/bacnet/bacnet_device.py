import logging

from BAC0.core.io.IOExceptions import NoResponseFromController, UnknownObjectError, \
    ReadPropertyMultipleException, APDUError

from visiobas_gateway.connectors.bacnet.object_property import ObjectProperty
from visiobas_gateway.connectors.bacnet.object_type import ObjectType


class BACnetDevice:
    def __init__(self, address: str, device_id: int, network, objects: dict):
        self.__logger = self.__logger = logging.getLogger(f'BACnet Device [{device_id}]')

        self.__address = address
        self.__device_id = device_id
        self.__network = network
        self.__objects2poll = objects

        self.__properties2poll = [
            ObjectProperty.PRESENT_VALUE,
            ObjectProperty.STATUS_FLAGS,
            # ObjectProperty.RELIABILITY
        ]

        # self.__objects_per_rpm = 25 todo: Should we use one rpm for several objects?

        self.__not_support_rpm = None

    def __rpm_object(self, object_type: ObjectType, object_id: int,
                     properties: list) -> str:
        properties_as_string = [prop.name for prop in properties]
        args_rpm = ' '.join(
            [self.__address, object_type.name, str(object_id), *properties_as_string])

        rpm_resp = self.__network.readMultiple(args_rpm)
        self.__logger.info(type(rpm_resp), rpm_resp)  # FIXME
        if rpm_resp:
            pass
            # todo: process statusFlags and etc
            # todo: verify
        else:
            # todo: set reliability
            raise NoResponseFromController

        return ' '.join([str(object_id), str(object_type.id), *rpm_resp]) + ';'

    def poll(self) -> str:

        polled_data = ''
        for object_type, objects_id in self.__objects2poll.items():
            for object_id in objects_id:
                data = None
                try:
                    data = self.__rpm_object(object_type=object_type,
                                             object_id=object_id,
                                             properties=self.__properties2poll)
                    # todo: process statusFlags and etc
                    # todo: verify

                except ReadPropertyMultipleException as e:
                    self.__logger.warning('RPM error for '
                                          f'({object_type.name}, {object_id}): {e} '
                                          'Trying to poll by RP ...')
                    # todo: remember that the object is non-readable by RPM
                    # todo: implement poll by RP
                    # data =

                except NoResponseFromController as e:
                    self.__logger.warning('No BACnet response from '
                                          f'({object_type.name}, {object_id}): {e} ')

                except UnknownObjectError as e:
                    self.__logger.error('Unknown BACnet object: '
                                        f'({object_type.name}, {object_id}): {e}')
                finally:
                    if data:
                        polled_data += data

        if polled_data:
            return polled_data
        else:
            self.__logger.critical('Cannot be polled.')
            raise NoResponseFromController

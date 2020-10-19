import logging
from threading import Thread

from BAC0.core.io.IOExceptions import NoResponseFromController, UnknownObjectError, \
    ReadPropertyMultipleException

from visiobas_gateway.connectors.bacnet.object_property import ObjectProperty
from visiobas_gateway.connectors.bacnet.object_type import ObjectType


class BACnetDevice(Thread):
    def __init__(self, gateway, address: str, device_id: int, network, objects: dict):
        super().__init__()

        self.__logger = self.__logger = logging.getLogger(f'BACnet-Device [{device_id}]')
        self.setName(name=f'BACnet Device [{device_id}]-Thread')

        self.__gateway = gateway

        self.__address = address
        self.__device_id = device_id
        self.__network = network
        self.__objects2poll = objects

        self.__properties2poll = [
            ObjectProperty.PRESENT_VALUE,
            ObjectProperty.STATUS_FLAGS,
        ]

        # self.__objects_per_rpm = 25
        # todo: Should we use one rpm for several objects?

        self.__not_support_rpm = False

        self.__polling = True

        self.start()

    def run(self):
        self.__logger.info('Started polling.')

        while self.__polling:
            try:
                data = self.start_poll()
                self.__gateway.post_device(device_id=self.__device_id,
                                           data=data)
            except Exception as e:
                self.__logger.error(f'Polling error: {e}')
        else:
            self.__logger.info('Stopped polling.')

    def stop_polling(self):
        self.__polling = False
        self.__logger.info('Stopping polling ...')

    def start_polling(self):
        self.__polling = True
        self.__logger.info('Starting polling ...')
        self.start()

    def __rpm_object(self, object_type: ObjectType, object_id: int,
                     properties: list) -> str:
        """
        RPM request for one object

        :param object_type:
        :param object_id:
        :param properties:
        :return:
        """
        properties_as_string = [prop.name for prop in properties]
        args_rpm = ' '.join(
            [self.__address, object_type.name, str(object_id), *properties_as_string])
        # rpm_resp = self.__network.readMultiple(args_rpm)
        # FIXME: temporarily. unfinished
        pv, sf = self.__network.readMultiple(args_rpm)

        if pv and sf:
            binary_sf = self.__status_flags_to_binary(status_flags=sf)
            return ' '.join([str(object_id),
                             str(object_type.id),
                             str(pv),
                             str(binary_sf),
                             ';'])
        else:
            raise NoResponseFromController
        # if rpm_resp:
        #     pass
        #     # todo: process statusFlags and etc
        #     # todo: verify
        # else:
        #     # todo: set reliability
        #     raise NoResponseFromController

    def __rp(self, object_type: ObjectType, object_id: int, property_: ObjectProperty):
        args_rp = ' '.join(
            [self.__address, object_type.name, str(object_id), property_.name])
        rp_resp = self.__network.read(args_rp)

        if rp_resp:
            return rp_resp
        else:
            raise NoResponseFromController

    def __simulate_rpm_object(self, object_type: ObjectType, object_id: int,
                              properties: list):
        # rp_resps = []
        #
        # for prop in properties:
        #     rp_resp = self.__rp(object_type=object_type,
        #                         object_id=object_id,
        #                         property_=prop)
        #     rp_resps.append(rp_resp)

        rp_resps = [self.__rp(object_type=object_type,
                              object_id=object_id,
                              property_=prop) for prop in properties]
        # FIXME: temporarily. unfinished
        if len(rp_resps) == 2:
            pv = rp_resps[0]
            sf = rp_resps[1]
            binary_sf = self.__status_flags_to_binary(status_flags=sf)
            return ' '.join([str(object_id),
                             str(object_type.id),
                             str(pv),
                             str(binary_sf),
                             ';'])

    @staticmethod
    def __status_flags_to_binary(status_flags: list) -> int:
        """
        Convert list with statusFlags to number by binary coding.

        :param status_flags: ex. [1, 0, 1, 0]
        :return: status_flags in binary coding.
            ex. [1, 0, 1, 0] -> 10
            (b1000 + b0010) = 10 in decimal
        """
        return int(''.join([str(flag) for flag in status_flags]), base=2)

    def start_poll(self) -> str:

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
                    data = self.__simulate_rpm_object(object_type=object_type,
                                                      object_id=object_id,
                                                      properties=self.__properties2poll)

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

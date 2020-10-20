import logging
import time
from pprint import pprint
from threading import Thread

from BAC0.core.io.IOExceptions import NoResponseFromController, UnknownObjectError, \
    ReadPropertyMultipleException

from visiobas_gateway.connectors.bacnet.object_property import ObjectProperty
from visiobas_gateway.connectors.bacnet.object_type import ObjectType


class BACnetDevice(Thread):
    def __init__(self, gateway, address: str, device_id: int, network, objects: dict):
        super().__init__()

        self.__device_id = device_id
        self.__logger = self.__logger = logging.getLogger(f'{self}')
        self.setName(name=f'{self}-Thread')

        self.__gateway = gateway

        self.__address = address
        self.__network = network
        self.__objects2poll = objects

        self.__properties2poll = [
            ObjectProperty.PRESENT_VALUE,
            ObjectProperty.STATUS_FLAGS,
        ]

        # self.__objects_per_rpm = 25
        # todo: Should we use one rpm for several objects?

        self.__not_support_rpm = {}
        self.__not_responding = {}
        self.__is_active = False

        self.__polling = True

        self.__logger.info(f'{self} starting ...')
        self.start()

    def __repr__(self):
        return f'BACnetDevice [{self.__device_id}]'

    def __len__(self):
        """Returns the quantity of objects in the device received from the server side"""
        return self.__count_objects(objects=self.__objects2poll)

    @staticmethod
    def __count_objects(objects: dict) -> int:
        """
        Counts the number of objects in the object dictionaries.
        Used in __len__
        """
        counter = 0
        for object_type in objects:
            counter += len(objects[object_type])
        # fixme: can be refactored
        return counter

    def run(self):
        while self.__polling:
            self.__logger.info('Polling started')
            try:
                t0 = time.time()
                data = self.poll()
                t1 = time.time()
                time_delta = t1 - t0
                self.__logger.info(f'{self} polled for {time_delta} sec')
                self.__gateway.post_device(device_id=self.__device_id,
                                           data=data)
                exit(666)  # FIXME delete
            except Exception as e:
                self.__logger.error(f'Polling error: {e}', exc_info=False)
        else:
            self.__logger.info(f'{self} stopped.')

    def start_polling(self):
        self.__polling = True
        self.__logger.info('Starting polling ...')
        self.start()

    def stop_polling(self):
        self.__polling = False
        self.__logger.info('Stopping polling ...')

    def set_inactive(self):
        # todo: push to connector for ping checking
        self.stop_polling()
        self.__logger.warning(f'{self} inactive.')

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
        try:
            pv, sf = self.__network.readMultiple(args_rpm)

            # convert active\inactive to 1\0
            if pv == 'active':
                pv = 1
            elif pv == 'inactive':
                pv = 0

        except ValueError:
            raise ReadPropertyMultipleException

        # todo: check parts

        if pv and sf:
            binary_sf = self.__status_flags_to_binary(status_flags=sf)
            return ' '.join([str(object_id),
                             str(object_type.id),
                             str(pv),
                             str(binary_sf)])
        else:
            raise ReadPropertyMultipleException

    def __rp(self, object_type: ObjectType, object_id: int, property_: ObjectProperty):
        """RP request for one property"""
        args_rp = ' '.join([self.__address,
                            object_type.name,
                            str(object_id),
                            property_.name])
        rp_response = self.__network.read(args_rp)
        if rp_response:
            self.set_not_support_rpm(object_type=object_type, object_id=object_id)
            return rp_response
        else:
            self.set_not_responding(object_type=object_type, object_id=object_id)
            raise NoResponseFromController

    def set_not_support_rpm(self, object_type: ObjectType, object_id: int) -> None:
        """Mark object as not supporting rpm"""
        if object_type in self.__not_support_rpm:
            self.__not_support_rpm[object_type].append(object_id)
        else:
            self.__not_support_rpm[object_type] = [object_id]
        self.__logger.debug(f'({object_type}, {object_id}) marked as not supporting RPM')

    def set_not_responding(self, object_type: ObjectType, object_id: int) -> None:
        """Mark object as not responding"""
        if object_type in self.__not_responding:
            self.__not_responding[object_type].append(object_id)
        else:
            self.__not_responding[object_type] = [object_id]
        self.__logger.debug(f'({object_type}, {object_id}) marked as not responding')

    def __simulate_rpm_object(self, object_type: ObjectType, object_id: int,
                              properties: list) -> str:
        try:
            rp_responses = [self.__rp(object_type=object_type,
                                      object_id=object_id,
                                      property_=prop) for prop in properties]
        except NoResponseFromController as e:
            self.__logger.warning(f'RP\'s error for ({object_type}, {object_id})')
            raise NoResponseFromController(f'RP error: {e}')

        # FIXME: temporarily. unfinished
        pv = rp_responses[0]
        sf = rp_responses[1]
        binary_sf = self.__status_flags_to_binary(status_flags=sf)
        return ' '.join([str(object_id),
                         str(object_type.id),
                         str(pv),
                         str(binary_sf)])

    @staticmethod
    def __status_flags_to_binary(status_flags: list) -> int:
        """
        Convert list with statusFlags to number by binary coding.

        :param status_flags: ex. [1, 0, 1, 0]
        :return: status_flags in binary coding.

            Example:
            -------
            [1, 0, 1, 0] -> 10
            (b1000 + b0010) = 10 in decimal
        """
        return int(''.join([str(flag) for flag in status_flags]), base=2)

    def __is_object_responding(self, object_type: ObjectType, object_id: int) -> bool:
        return object_id not in self.__not_responding.get(object_type, [])

    def poll(self) -> str:
        polled_data = []
        for object_type, objects_id in self.__objects2poll.items():
            for object_id in objects_id:
                if self.__is_object_responding(object_type=object_type,
                                               object_id=object_id):
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
                        try:
                            data = self.__simulate_rpm_object(object_type=object_type,
                                                              object_id=object_id,
                                                              properties=self.__properties2poll)
                        except (ValueError, NoResponseFromController) as e:
                            self.__logger.warning(f'PRM simulation error: {e}')

                    except NoResponseFromController as e:
                        self.__logger.warning('No BACnet response from '
                                              f'({object_type.name}, {object_id}): {e} ')

                    except UnknownObjectError as e:
                        self.__logger.error('Unknown BACnet object: '
                                            f'({object_type.name}, {object_id}): {e}')
                    finally:
                        if data:
                            polled_data.append(data)
                else:  # object not responding
                    pass

        if polled_data:
            self.__logger.info("////////////////////////////////////////\n"
                               f'{len(polled_data)} out of {len(self)} objects were polled.\n'
                               f'Not support RPM: {self.__count_objects(self.__not_support_rpm)}\n'
                               f'Not responding: {self.__count_objects(self.__not_responding)}\n'
                               '////////////////////////////////////////')
            self.__logger.info('COLLECTED: ')
            pprint(polled_data)
            return ';'.join(polled_data)
        else:
            self.__logger.critical('No objects were successfully polled')
            self.set_inactive()
            # todo: What we should doing with inactive device?
            #   push to connector to check ping?

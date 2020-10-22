import logging
import time
from threading import Thread

from visiobas_gateway.connectors.bacnet.object import Object
from visiobas_gateway.connectors.bacnet.object_property import ObjectProperty


class BACnetDevice(Thread):
    def __init__(self, gateway, address: str, device_id: int, network, objects: dict):
        super().__init__()

        self.__device_id = device_id
        self.__logger = self.__logger = logging.getLogger(f'{self}')
        self.setName(name=f'{self}-Thread')

        self.__gateway = gateway

        self.address = address
        self.network = network
        self.__objects2poll = objects

        self.__objects = set()

        self.__properties2poll = [
            ObjectProperty.presentValue,
            ObjectProperty.statusFlags,
        ]

        # self.__objects_per_rpm = 25
        # todo: Should we use one RPM for several objects?

        self.__not_support_rpm = {}
        self.__not_responding = {}
        self.__unknown_objects = {}

        self.__polling = True

        self.__logger.info(f'{self} starting ...')
        self.start()

    def __repr__(self):
        return f'BACnetDevice [{self.__device_id}]'

    def __len__(self):
        """
        :return: the quantity of objects in the device received from the server side
        """
        return self.__count_objects(objects=self.__objects2poll)

    @staticmethod
    def __count_objects(objects: dict) -> int:
        """
        Used in __len__, statistic

        :param objects: object dictionary
        :return: the number of objects in the object dictionary
        """
        counter = 0
        for object_type in objects:
            counter += len(objects[object_type])
        # fixme: can be refactored: change to set of tuple
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
                self.__logger.error(f'Polling error: {e}', exc_info=True)
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
        # todo: What we should doing with inactive device?
        #   push to connector to check ping?

    # def __rpm_object(self, object_type: ObjectType, object_id: int,
    #                  properties: list) -> str:
    #     """
    #     RPM request for one object
    #
    #     :param object_type:
    #     :param object_id:
    #     :param properties:
    #     :return:
    #     """
    #     properties_as_string = [prop.name for prop in properties]
    #     args_rpm = ' '.join([self.address,
    #                          object_type.name,
    #                          str(object_id),
    #                          *properties_as_string])
    #     # FIXME: temporarily
    #     try:
    #         pv, sf = self.network.readMultiple(args_rpm)
    #
    #     except ValueError:
    #         raise ReadPropertyMultipleException
    #
    #     # todo: check parts
    #
    #     if pv and sf:
    #         # convert active\inactive to 1\0
    #         if pv == 'active':
    #             pv = 1
    #         elif pv == 'inactive':
    #             pv = 0
    #
    #         binary_sf = self.__status_flags_to_binary(status_flags=sf)
    #         return ' '.join([str(object_id),
    #                          str(object_type.id),
    #                          str(pv),
    #                          str(binary_sf)])
    #     else:
    #         raise ReadPropertyMultipleException

    # def __rp(self, object_type: ObjectType, object_id: int, property_: ObjectProperty):
    #     """RP request for one property"""
    #     args_rp = ' '.join([self.address,
    #                         object_type.name,
    #                         str(object_id),
    #                         property_.name])
    #     rp_response = self.network.read(args_rp)
    #     if rp_response:
    #         self.mark_object(object_type=object_type, object_id=object_id,
    #                          not_support_rpm=True)
    #         return rp_response
    #     else:
    #         self.mark_object(object_type=object_type, object_id=object_id,
    #                          not_responding=True)
    #         raise NoResponseFromController

    # def mark_object(self, object_type: ObjectType, object_id: int,
    #                 *,
    #                 not_support_rpm: bool = False,
    #                 not_responding: bool = False,
    #                 unknown_object: bool = False
    #                 ) -> None:
    #     if not_support_rpm:
    #         self.__mark_object(object_type=object_type,
    #                            object_id=object_id,
    #                            objects=self.__not_support_rpm)
    #         self.__logger.debug(f'({object_type}, {object_id}) '
    #                             'marked as not supporting RPM')
    #     if not_responding:
    #         self.__mark_object(object_type=object_type,
    #                            object_id=object_id,
    #                            objects=self.__not_responding)
    #         self.__logger.debug(f'({object_type}, {object_id}) '
    #                             'marked as not responding')
    #     if unknown_object:
    #         self.__mark_object(object_type=object_type,
    #                            object_id=object_id,
    #                            objects=self.__unknown_objects)
    #         self.__logger.debug(f'({object_type}, {object_id}) '
    #                             'marked as unknown object')

    # @staticmethod
    # def __mark_object(object_type: ObjectType, object_id: int, objects: dict) -> None:
    #     # todo: in dict change lists to sets OR change dict to set of tuples
    #
    #     if object_type in objects:
    #         objects[object_type].append(object_id)
    #     else:
    #         objects[object_type] = [object_id]

    # def __simulate_rpm_object(self, object_type: ObjectType, object_id: int,
    #                           properties: list) -> str:
    #     try:
    #         rp_responses = [self.__rp(object_type=object_type,
    #                                   object_id=object_id,
    #                                   property_=prop) for prop in properties]
    #     except NoResponseFromController as e:
    #         self.__logger.warning(f'RP\'s error for ({object_type}, {object_id})')
    #         raise NoResponseFromController(f'RP error: {e}')
    #
    #     # FIXME: temporarily. unfinished
    #     pv = rp_responses[0]
    #     # convert active\inactive to 1\0
    #     if pv == 'active':
    #         pv = 1
    #     elif pv == 'inactive':
    #         pv = 0
    #
    #     sf = rp_responses[1]
    #     binary_sf = self.__status_flags_to_binary(status_flags=sf)
    #     return ' '.join([str(object_id),
    #                      str(object_type.id),
    #                      str(pv),
    #                      str(binary_sf)])

    # @staticmethod
    # def __status_flags_to_binary(status_flags: list) -> int:
    #     """
    #     Convert list with statusFlags to number by binary coding.
    #
    #     :param status_flags: ex. [1, 0, 1, 0]
    #     :return: status_flags in binary coding.
    #
    #         Example:
    #         -------
    #         [1, 0, 1, 0] -> 10
    #         (b1000 + b0010) = 10 in decimal
    #     """
    #     # todo: move in to SF class
    #     return int(''.join([str(flag) for flag in status_flags]), base=2)

    # def __is_object_responding(self, object_type: ObjectType, object_id: int) -> bool:
    #     return object_id not in self.__not_responding.get(object_type, [])
    #     # todo: change to interface as mark_object

    def poll(self) -> str:
        while self.__polling:
            polled_data = []
            for object_type, objects_id in self.__objects2poll.items():
                for object_id in objects_id:
                    obj = Object(device=self, type_=object_type, id_=object_id)
                    try:
                        values = obj.read(properties=self.__properties2poll)
                        evaluated_values = obj.evaluate(values=values)
                    except Exception as e:
                        raise Exception(f'{obj} Poll Error: {e}')
                    else:
                        data_str = obj.as_str(properties=evaluated_values)
                        polled_data.append(data_str)

                    # todo: How much objects need to switch into inactive?

            if polled_data:
                # self.__logger.info("\n////////////////////////////////////////\n"
                #                    f'{len(polled_data)} out of {len(self)} objects were polled.\n'
                #                    f'Not support RPM: {self.__count_objects(self.__not_support_rpm)}\n'
                #                    f'Not responding: {self.__count_objects(self.__not_responding)}\n'
                #                    f'Unknown objects: {self.__count_objects(self.__unknown_objects)}\n'
                #                    '////////////////////////////////////////')
                request_body = ';'.join(polled_data) + ';'
                return request_body
            else:
                self.__logger.critical('No objects were successfully polled')
                self.set_inactive()

                # if self.__is_object_responding(object_type=object_type,
                #                                object_id=object_id):
                #     data = None
                #     try:
                #         data = self.__rpm_object(object_type=object_type,
                #                                  object_id=object_id,
                #                                  properties=self.__properties2poll)
                #         # todo: process statusFlags and etc
                #         # todo: verify
                #
                #     except ReadPropertyMultipleException as e:
                #         self.__logger.warning('RPM error for '
                #                               f'({object_type.name}, {object_id}): {e} '
                #                               'Trying to poll by RP ...')
                #         try:
                #             data = self.__simulate_rpm_object(object_type=object_type,
                #                                               object_id=object_id,
                #                                               properties=self.__properties2poll)
                #         except (ValueError, NoResponseFromController) as e:
                #             self.__logger.warning(f'PRM simulation error: {e}')
                #
                #     except NoResponseFromController as e:
                #         self.__logger.warning('No BACnet response from '
                #                               f'({object_type.name}, {object_id}): {e} ')
                #
                #     except UnknownObjectError as e:
                #         self.mark_object(object_type=object_type, object_id=object_id,
                #                          unknown_object=True)
                #         self.__logger.error('Unknown BACnet object: '
                #                             f'({object_type.name}, {object_id}): {e}')
                #     finally:
                #         if data:
                #             polled_data.append(data)
                # else:  # object not responding
                #     pass

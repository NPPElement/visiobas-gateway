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

        self.__not_support_rpm = set()
        self.__not_responding = set()
        self.__unknown_objects = set()

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

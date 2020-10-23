import asyncio
import logging
import time
from pathlib import Path
from threading import Thread, RLock

from visiobas_gateway.connectors.bacnet.object import Object
from visiobas_gateway.connectors.bacnet.object_property import ObjectProperty


class BACnetDevice(Thread):
    def __init__(self, gateway, address: str, device_id: int, network, objects: dict):
        super().__init__()

        self.__lock = RLock()

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

        self.__active = True

        self.not_support_rpm = set()
        self.not_responding = set()
        self.unknown_objects = set()

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

    def log_in_file(self, time_: float, polled_objects: int) -> None:
        base_dir = Path(__file__).resolve().parent.parent
        log_file = base_dir / 'log/log.txt'
        self.__lock.acquire()
        with open(file=log_file, mode='a', encoding='utf-8') as file:
            file.write(
                '=================================================='
                f'{self} polled for {round(time_, ndigits=2)} seconds'
                f'Polled objects: {polled_objects}/{len(self)}'
                f'Objects not support RPM: {len(self.not_support_rpm)}'
                f'Objects not responding: {len(self.not_responding)}'
                f'Unknown objects: {len(self.unknown_objects)}'
                '=================================================='
            )
        self.__lock.release()

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
            if self.__active:
                try:
                    t0 = time.time()
                    data = self.poll()
                    t1 = time.time()
                    time_delta = t1 - t0
                    self.log_in_file(time_=time_delta, polled_objects=len(data))
                    if data:
                        self.__logger.info(f'{self} polled for {time_delta} sec')
                        self.__gateway.post_device(device_id=self.__device_id,
                                                   data=data)

                except Exception as e:
                    self.__logger.error(f'Polling error: {e}', exc_info=True)
            else:  # if device inactive
                if self.network.whois(f'{self.address}'):
                    self.__active = True
                    continue
                # delay
                # todo: move delay in config

                # todo: close Thread and push to bacnet-connector
                asyncio.run(asyncio.sleep(delay=60))
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
        # self.stop_polling()
        self.__active = False
        self.__logger.warning(f'{self} switched to inactive.')

    def poll(self) -> str:
        limit = 25  # to switch to inactive
        # todo move to cfg
        while self.__polling:
            polled_data = []
            no_res_in_row = 0
            for object_type, objects_id in self.__objects2poll.items():
                for object_id in objects_id:
                    if no_res_in_row < limit:
                        obj = Object(device=self, type_=object_type, id_=object_id)

                        try:
                            values = obj.read(properties=self.__properties2poll)
                            evaluated_values = obj.evaluate(values=values)
                        except Exception as e:
                            no_res_in_row += 1
                            raise Exception(f'{obj} Poll Error: {e}')
                        else:
                            if evaluated_values:
                                data_str = obj.as_str(properties=evaluated_values)
                                polled_data.append(data_str)
                            else:
                                no_res_in_row += 1
                    else:
                        self.set_inactive()
                        return ''

                    # todo: How much objects need to switch into inactive?

            if polled_data:
                request_body = ';'.join(polled_data) + ';'
                return request_body
            else:
                self.__logger.critical('No objects were successfully polled')
                self.set_inactive()
                return ''

import asyncio
import logging
import time
from logging.handlers import RotatingFileHandler
from threading import Thread

from BAC0.core.io.IOExceptions import ReadPropertyException

from visiobas_gateway.connectors.bacnet.object import Object
from visiobas_gateway.connectors.bacnet.object_property import ObjectProperty
from visiobas_gateway.connectors.bacnet.object_type import ObjectType

LOGGER_FORMAT = '%(levelname)-8s [%(asctime)s] [%(threadName)s] %(name)s - (%(filename)s).%(funcName)s(%(lineno)d): %(message)s'


class BACnetDevice(Thread):
    def __init__(self, gateway, address: str, device_id: int, network, objects: dict):
        super().__init__()

        self.__device_id = device_id

        self.__logger = self.__logger = logging.getLogger(f'{self}')
        handler = RotatingFileHandler(filename=f'{device_id}.log',
                                      mode='a',
                                      maxBytes=5_000_000,
                                      encoding='utf-8'
                                      )
        formatter = logging.Formatter(LOGGER_FORMAT)
        handler.setFormatter(formatter)
        self.__logger.addHandler(handler)

        self.setName(name=f'{self}-Thread')

        self.__gateway = gateway

        self.address = address
        self.network = network
        # self.__objects2poll = objects

        self.__objects = set()
        self.unpack_objects(objects=objects)

        self.__properties2poll = [
            ObjectProperty.presentValue,
            ObjectProperty.statusFlags,
        ]

        # self.__objects_per_rpm = 25
        # todo: Should we use one RPM for several objects?

        self.__active = True

        self.not_support_rpm = set()
        # self.not_responding = set()
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
        # return self.__count_objects(objects=self.__objects2poll)
        return len(self.__objects)

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

                    self.__logger.info(
                        '\n==================================================\n'
                        f'{self} ip:{self.address} polled for {round(time_delta, ndigits=2)} seconds\n'
                        f'Objects: {len(self)}\n'
                        f'Objects not support RPM: {len(self.not_support_rpm)}\n'
                        # f'Objects not responding: {len(self.not_responding)}\n'
                        f'Unknown objects: {len(self.unknown_objects)}\n'
                        '==================================================')
                    if data:
                        # self.__logger.info(f'{self} polled for {time_delta} sec')
                        self.__gateway.post_device(device_id=self.__device_id,
                                                   data=data)
                        self.__logger.info(f'Collected data: {data} was sent to server')

                except Exception as e:
                    self.__logger.error(f'Polling error: {e}')  #, exc_info=True)
            else:  # if device inactive
                try:
                    device_obj = Object(device=self, type_=ObjectType.DEVICE,
                                        id_=self.__device_id)
                    device_id = device_obj.read_property(
                        property_=ObjectProperty.objectIdentifier)
                    self.__logger.info(f'PING: device_id: {device_id}')

                    if device_id:
                        self.__active = True
                        continue
                except ReadPropertyException:
                    continue
                except Exception:
                    continue
                # delay
                # todo: move delay in config

                # todo: close Thread and push to bacnet-connector
                asyncio.run(asyncio.sleep(delay=60))
            # exit(666)
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
        self.__logger.info('Set inactive')

        # base_dir = Path(__file__).resolve().parent.parent
        # log_file = base_dir / 'log/log.txt'
        # self.__lock.acquire()
        # with open(file=log_file, mode='a', encoding='utf-8') as file:
        #     file.write(
        #         '=================================================='
        #         f'{self} ip:{self.address} switched to inactive.'
        #         '=================================================='
        #     )
        # self.__lock.release()

        self.__logger.warning(f'{self} switched to inactive.')

    def poll(self) -> str:
        while self.__polling:
            polled_data = []
            for obj in self.__objects:
                try:
                    evaluated_values = None
                    values = obj.read(properties=self.__properties2poll)
                    self.__logger.debug(f'Values: {values}')
                    if values:
                        evaluated_values = obj.evaluate(values=values)
                except Exception as e:
                    self.__logger.error(f'{e}', exc_info=True)
                    # raise Exception(f'{obj} Poll Error: {e}')
                else:
                    self.__logger.debug(f'Evaluated values: {evaluated_values}')
                    if evaluated_values:
                        data_str = obj.as_str(properties=evaluated_values)
                        self.__logger.debug(f'Data_str: {data_str}')
                        polled_data.append(data_str)

            if polled_data:
                self.__logger.debug(f'Polled objects: {len(polled_data)}')
                request_body = ';'.join(polled_data) + ';'
                return request_body
            else:
                self.__logger.warning('No objects were successfully polled')
                self.set_inactive()
                return ''

    def unpack_objects(self, objects: dict) -> None:
        for object_type, objects_id in objects.items():
            for object_id in objects_id:
                obj = Object(device=self, type_=object_type, id_=object_id)
                self.__objects.add(obj)

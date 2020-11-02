import logging
from logging.handlers import RotatingFileHandler
from multiprocessing import SimpleQueue
from pathlib import Path
from threading import Thread
from time import sleep, time

from BAC0.core.io.IOExceptions import ReadPropertyException

from vb_gateway.connectors.bacnet.object import BACnetObject
from vb_gateway.connectors.bacnet.object_property import ObjProperty
from vb_gateway.connectors.bacnet.object_type import ObjType
from vb_gateway.connectors.bacnet.status_flags import StatusFlags


class BACnetDevice(Thread):
    def __init__(self, gateway,
                 client_queue: SimpleQueue,
                 connector,
                 address: str,
                 device_id: int,
                 network,
                 objects: dict):
        super().__init__()

        self.__device_id = device_id

        self.__logger = self.__logger = logging.getLogger(f'{self}')

        base_path = Path(__file__).resolve().parent.parent.parent
        log_path = base_path / f'logs/{device_id}.log'
        handler = RotatingFileHandler(filename=log_path,
                                      mode='a',
                                      maxBytes=50_000,
                                      encoding='utf-8'
                                      )
        LOGGER_FORMAT = '%(levelname)-8s [%(asctime)s] [%(threadName)s] %(name)s - (%(filename)s).%(funcName)s(%(lineno)d): %(message)s'
        formatter = logging.Formatter(LOGGER_FORMAT)
        handler.setFormatter(formatter)
        self.__logger.addHandler(handler)

        self.setName(name=f'{self}-Thread')
        self.setDaemon(True)

        self.__gateway = gateway
        self.__connector = connector
        self.__client_queue = client_queue

        self.address = address
        self.network = network

        self.objects = set()
        self.__unpack_objects(objects=objects)

        # TODO: move to connector:
        self.__BI_AI_MI_AC = {
            ObjType.BINARY_INPUT,
            ObjType.ANALOG_INPUT,
            ObjType.MULTI_STATE_INPUT,
        }

        self.__BI_AI_MI_AC_properties = [
            ObjProperty.presentValue,
            ObjProperty.statusFlags,
        ]

        self.__BO_BV_AO_AV_MV_MO = {
            ObjType.BINARY_OUTPUT,
            ObjType.BINARY_VALUE,
            ObjType.ANALOG_OUTPUT,
            ObjType.ANALOG_VALUE,
            ObjType.MULTI_STATE_VALUE,
            ObjType.MULTI_STATE_OUTPUT
        }

        self.__BO_BV_AO_AV_MV_MO_properties = [
            ObjProperty.presentValue,
            ObjProperty.statusFlags,
            ObjProperty.priorityArray
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
        :return: the quantity of objects in the device received from the server
        """
        return len(self.objects)

    # def __hash__(self):
    #     return hash(self.objects)

    # def __eq__(self, other):
    #     return self.objects is other.objects

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
                    t0 = time()
                    self.poll()
                    t1 = time()
                    time_delta = t1 - t0

                    self.__logger.info(
                        '\n==================================================\n'
                        f'{self} ip:{self.address} polled for {round(time_delta, ndigits=2)} seconds\n'
                        f'Objects: {len(self)}\n'
                        f'Objects not support RPM: {len(self.not_support_rpm)}\n'
                        # f'Objects not responding: {len(self.not_responding)}\n'
                        f'Unknown objects: {len(self.unknown_objects)}\n'
                        '==================================================')
                    # if data:
                    #     # self.__logger.info(f'{self} polled for {time_delta} sec')
                    #     # self.__gateway.post_device(device_id=self.__device_id,
                    #     #                            data=data)
                    #     # self.__logger.info(f'Collected data: {data} was sent to server')

                except Exception as e:
                    self.__logger.error(f'Polling error: {e}')  # , exc_info=True)
            else:  # if device inactive
                try:
                    device_obj = BACnetObject(device=self, type_=ObjType.DEVICE,
                                              id_=self.__device_id)
                    device_id = device_obj.read_property(
                        property_=ObjProperty.objectIdentifier)
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
                sleep(60)
            # exit(666)
        else:
            self.__logger.info(f'{self} stopped.')

    def start_polling(self):
        self.__polling = True
        self.__logger.info('Starting polling ...')
        self.start()

    def stop_polling(self):
        self.__polling = False

        # Allows HTTP Client send collected objs to server
        # self.put_device_end_to_verifier()

        self.__logger.info('Stopping polling ...')

    def set_inactive(self):
        self.__active = False
        self.__logger.info('Set inactive')
        self.__logger.warning(f'{self} switched to inactive.')

    def poll(self) -> None:
        while self.__polling:
            for obj in self.objects:
                properties = {
                    ObjProperty.deviceId: self.__device_id,
                    ObjProperty.objectType: obj.type,
                    ObjProperty.objectIdentifier: obj.id,
                    ObjProperty.objectName: obj.name
                }
                try:
                    if not obj.is_unknown:
                        if obj.type in self.__BI_AI_MI_AC:
                            values = obj.read(properties=self.__BI_AI_MI_AC_properties)
                        elif obj.type in self.__BO_BV_AO_AV_MV_MO:
                            values = obj.read(
                                properties=self.__BO_BV_AO_AV_MV_MO_properties)
                        else:
                            self.__logger.warning(f'Unexpected ObjType: {obj.type}')
                            raise NotImplementedError

                    else:  # if obj is unknown
                        values = self.__get_unknown_obj_properties()

                except Exception as e:
                    self.__logger.error(f'{e}', exc_info=True)
                else:
                    if values:
                        properties.update(values)
                        # send data into Verifier-process
                        self.__put_data_into_verifier(properties=properties)

                    self.__logger.debug(f'From {obj} received: {properties}')
                    self.__put_data_into_verifier(properties=properties)

            # notify verifier, that device polled and should send collected objects via HTTP
            self.__put_device_end_to_verifier()
        else:
            self.__logger.info(f'{self} stopped.')

            #         self.__logger.debug(f'VALUES: {values}')
            #         if values:
            #             evaluated_values = obj.evaluate(values=values)
            #             self.__logger.debug(f'EVALUATED VALUES: {evaluated_values}')
            #         if evaluated_values:
            #             data_str = obj.as_str(properties=evaluated_values)
            #             self.__logger.debug(f'DATA_STR: {data_str}')
            #             polled_data.append(data_str)
            #     except Exception as e:
            #         self.__logger.error(f'{e}', exc_info=True)
            #         # raise Exception(f'{obj} Poll Error: {e}')
            #
            # if polled_data:
            #     self.__logger.debug(f'Polled objects: {len(polled_data)}')
            #     request_body = ';'.join(polled_data) + ';'
            #     return request_body
            # else:
            #     self.__logger.warning('No objects were successfully polled')
            #     self.set_inactive()
            #     return ''

    @staticmethod
    def __get_unknown_obj_properties() -> dict:
        """ Returns properties for unknown objects
        """
        return {
            ObjProperty.presentValue: 'null',
            ObjProperty.statusFlags: StatusFlags([0, 1, 0, 0]),  # fault flag
            ObjProperty.reliability: 65
            #  todo: make reliability class as Enum
        }

    def __put_device_end_to_verifier(self) -> None:
        """ device_id in queue means that device polled.
            Should send collected objects to HTTP
        """
        self.__connector.queue.put(self.__device_id)

    def __put_data_into_verifier(self, properties: dict) -> None:
        """ Send collected data about obj into BACnetVerifier
        """
        self.__connector.queue.put(properties)

    def __unpack_objects(self, objects: dict) -> None:
        """ Uses to create objects at Device init
        """
        for obj_type, obj_properties in objects.items():
            for obj_id, obj_name in obj_properties:
                obj = BACnetObject(device=self,
                                   type_=obj_type,
                                   id_=obj_id,
                                   name=obj_name
                                   )
                self.objects.add(obj)

from multiprocessing import SimpleQueue
from pathlib import Path
from threading import Thread
from time import sleep, time

from BAC0.core.io.IOExceptions import ReadPropertyException, NoResponseFromController, \
    UnknownObjectError, UnknownPropertyError, ReadPropertyMultipleException

from vb_gateway.connectors.bacnet.obj_property import ObjProperty
from vb_gateway.connectors.bacnet.obj_type import ObjType
from vb_gateway.connectors.bacnet.object import BACnetObject
from vb_gateway.connectors.utils import get_fault_obj_properties
from vb_gateway.utility.utility import get_file_logger


class BACnetDevice(Thread):
    def __init__(self,
                 verifier_queue: SimpleQueue,
                 connector,
                 address: str,
                 device_id: int,
                 network,
                 objects: set[BACnetObject],
                 update_period: int = 10):
        super().__init__()

        __slots__ = ('id', 'update_period', '__logger', '__connector', '__verifier_queue',
                     'address', 'network', 'support_rpm', 'not_support_rpm',
                     '__BI_AI_MI_AC', '__BI_AI_MI_AC_properties',
                     '__BO_BV_AO_AV_MV_MO', '__BO_BV_AO_AV_MV_MO_properties',
                     '__active', '__polling')

        self.id = device_id
        self.update_period = update_period

        base_path = Path(__file__).resolve().parent.parent.parent
        log_file_path = base_path / f'logs/{__name__}{self.id}.log'

        self.__logger = get_file_logger(logger_name=f'{self}',
                                        file_size_bytes=50_000_000,
                                        file_path=log_file_path)

        self.setName(name=f'{self}-Thread')
        self.setDaemon(True)

        self.__connector = connector
        self.__verifier_queue = verifier_queue

        self.address = address
        self.network = network

        self.support_rpm = objects
        self.not_support_rpm: set[BACnetObject] = set()

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
            ObjType.BINARY_OUTPUT, ObjType.BINARY_VALUE,
            ObjType.ANALOG_OUTPUT, ObjType.ANALOG_VALUE,
            ObjType.MULTI_STATE_VALUE, ObjType.MULTI_STATE_OUTPUT
        }

        self.__BO_BV_AO_AV_MV_MO_properties = [
            ObjProperty.presentValue,
            ObjProperty.statusFlags,
            ObjProperty.priorityArray
        ]

        # self.__objects_per_rpm = 25
        # todo: Should we use one RPM for several objects?

        self.__active = True
        self.__polling = True

        self.__logger.info(f'{self} starting ...')
        self.start()

    def __repr__(self):
        return f'BACnetDevice [{self.id}]'

    def __len__(self):
        """ :return: the quantity of objects in the device received from the server
        """
        return len(self.support_rpm) + len(self.not_support_rpm)

    def run(self):
        while self.__polling:
            self.__logger.debug('Polling started')
            if self.__active:
                self.__logger.debug(f'{self} is active')
                try:
                    t0 = time()
                    self.__logger.info(f't0 = {t0}')

                    self.poll()  # poll all objects

                    t1 = time()
                    self.__logger.info(f't1 = {t1}')
                    time_delta = t1 - t0

                    self.__logger.info(
                        '\n==================================================\n'
                        f'{self} ip:{self.address} polled '
                        f'for {round(time_delta, ndigits=2)} seconds\n'
                        f'Objects: {len(self)}\n'
                        f'Objects not support RPM: {len(self.not_support_rpm)}\n'
                        '==================================================')

                    self.__logger.info(f'Timedelta = {time_delta}, upd_period = {self.update_period}')
                    if time_delta < self.update_period:
                        waiting_time = self.update_period - time_delta
                        self.__logger.info(
                            f'{self} Sleeping {round(waiting_time, ndigits=2)} sec ...')
                        sleep(waiting_time)

                except Exception as e:
                    self.__logger.error(f'Polling error: {e}')  # , exc_info=True)
            else:  # if device inactive
                self.__logger.debug(f'{self} is inactive')
                try:
                    device_obj = BACnetObject(type=ObjType.DEVICE,
                                              id=self.id,
                                              name='None')
                    device_id = self.read_property(obj=device_obj,
                                                   prop=ObjProperty.objectIdentifier)

                    self.__logger.info(f'PING: device_id: {device_id} <{type(device_id)}>')

                    if device_id:
                        self.__logger.debug(f'{self} setting to active ...')
                        self.__active = True
                        continue
                except Exception as e:
                    self.__logger.error(f"'Ping checking' error: {e}")
                    pass
                # delay
                # todo: move delay in config

                # todo: close Thread and push to bacnet-connector
                self.__logger.debug('Sleeping 60 sec ...')
                sleep(60)
        else:
            self.__logger.info(f'{self} stopped.')

    def start_polling(self) -> None:
        self.__polling = True
        self.__logger.info('Starting polling ...')
        self.start()

    def stop_polling(self) -> None:
        self.__polling = False
        self.__logger.info('Stopping polling ...')

    def set_inactive(self) -> None:
        self.__active = False
        # self.__logger.info('Set inactive')
        self.__logger.warning(f'{self} switched to inactive.')

        # TODO put to bacnet connector for ping checking

    def poll(self) -> None:
        """ Poll all object from device and.
            Send each object into verifier after answer.
            When all objects polled, send device_id into verifier as finish signal
        """
        for obj in self.support_rpm:
            self.__logger.debug(f'Polling supporting PRM {obj} ...')
            try:
                values = self.rpm(obj=obj)
                self.__logger.debug(f'{obj} values: {values}')
            except ReadPropertyMultipleException as e:
                self.__logger.error(f'{obj} rpm error: {e} '
                                    f'Marking as not supporting RPM ...')
                self.not_support_rpm.update(obj)
                self.support_rpm.discard(obj)

            except Exception as e:
                self.__logger.error(f'{obj} polling error: {e}', exc_info=True)
            else:
                self.__logger.debug(f'From {obj} read: {values}. Sending to verifier ...')
                self.__put_data_into_verifier(properties=values)

        for obj in self.not_support_rpm:
            self.__logger.debug(f'Polling not supporting PRM {obj} ...')
            try:
                values = self.simulate_rpm(obj=obj)
            except Exception as e:
                self.__logger.error(f'{obj} polling error: {e}', exc_info=True)
            else:
                self.__logger.debug(f'From {obj} read: {values}. Sending to verifier ...')
                self.__put_data_into_verifier(properties=values)

        # notify verifier, that device polled and should send collected objects via HTTP
        self.__logger.debug('All objects were polled. Send device_id to verifier')
        self.__put_device_end_to_verifier()

    def read_property(self, obj: BACnetObject, prop: ObjProperty):
        try:
            request = ' '.join([
                self.address,
                obj.type.name,
                str(obj.id),
                prop.name
            ])
            response = self.network.read(request)
        # except UnknownPropertyError:
        #     return self.__get_fault_obj_properties(reliability='unknown-property')
        # except UnknownObjectError:
        #     return self.__get_fault_obj_properties(reliability='unknown-object')
        # except NoResponseFromController:
        #     return self.__get_fault_obj_properties(reliability='no-response')
        except Exception as e:
            self.__logger.error(f'RP Error: {e}')
            raise e
            # return self.__get_fault_obj_properties(reliability='rp-error')
        else:
            if response is not None:
                if isinstance(response, str) and response.strip():
                    raise ReadPropertyException
                return response
            raise ReadPropertyException('Response is None')

    def read_property_multiple(self, obj: BACnetObject,
                               properties: list[ObjProperty]) -> dict:
        try:
            request = ' '.join([
                self.address,
                obj.type.name,
                str(obj.id),
                *[prop.name for prop in properties]
            ])
            response = self.network.readMultiple(request)

            # check values for None and empty strings
            values = {properties[i]: value for i, value in enumerate(response)
                      if value is not None and str(value).strip()}

        except Exception as e:
            self.__logger.error(f'RPM Error: {e}')
            raise ReadPropertyMultipleException(e)
        else:
            if values is not None:
                return values
            else:
                raise ReadPropertyMultipleException('Response is None')

    def __simulate_rpm(self, obj: BACnetObject, properties: list[ObjProperty]) -> dict:
        values = {}
        for prop in properties:
            try:
                response = self.read_property(obj=obj, prop=prop)

            except (UnknownObjectError, NoResponseFromController) as e:
                self.__logger.error(f'sRPM Error: {e}')
                raise e

            except (UnknownPropertyError, ReadPropertyException) as e:
                if prop is ObjProperty.priorityArray:
                    continue
                self.__logger.error(f'sRPM Error: {e}')
                raise e

            else:
                # read_property checks errors -> just update
                values.update({prop: response})
                self.not_support_rpm.update(obj)

        return values

    def rpm(self, obj: BACnetObject) -> dict:
        properties = {
            ObjProperty.deviceId: self.id,
            ObjProperty.objectName: obj.name,
            ObjProperty.objectType: obj.type,
            ObjProperty.objectIdentifier: obj.id,
        }
        try:
            if obj.type in self.__BI_AI_MI_AC:
                values = self.read_property_multiple(
                    obj=obj,
                    properties=self.__BI_AI_MI_AC_properties)

            elif obj.type in self.__BO_BV_AO_AV_MV_MO:
                values = self.read_property_multiple(
                    obj=obj,
                    properties=self.__BO_BV_AO_AV_MV_MO_properties)

            else:
                raise NotImplementedError(
                    'Now implemented only 9 types. Please provide one of: '
                    f'{[*self.__BI_AI_MI_AC, *self.__BO_BV_AO_AV_MV_MO]}')

        except ReadPropertyMultipleException as e:
            self.__logger.error(f'Read Error: {e}')
            self.not_support_rpm.update(obj)
            raise e
        else:
            properties.update(values)
            return properties

    def simulate_rpm(self, obj: BACnetObject) -> dict:
        properties = {
            ObjProperty.deviceId: self.id,
            ObjProperty.objectName: obj.name,
            ObjProperty.objectType: obj.type,
            ObjProperty.objectIdentifier: obj.id,
        }

        try:
            if obj.type in self.__BI_AI_MI_AC:
                values = self.__simulate_rpm(
                    obj=obj,
                    properties=self.__BI_AI_MI_AC_properties)
            elif obj.type in self.__BO_BV_AO_AV_MV_MO:
                values = self.__simulate_rpm(
                    obj=obj,
                    properties=self.__BO_BV_AO_AV_MV_MO_properties)
            else:
                raise NotImplementedError(
                    'Now implemented only 9 types. Please provide one of: '
                    f'{[*self.__BI_AI_MI_AC, *self.__BO_BV_AO_AV_MV_MO]}')

        except Exception as e:
            self.__logger.error(f'Read Error: {e}')
            if e is NoResponseFromController:
                values = get_fault_obj_properties(reliability='no-response')
            elif e is UnknownPropertyError:
                values = get_fault_obj_properties(reliability='unknown-property')
            elif e is UnknownObjectError:
                values = get_fault_obj_properties(reliability='unknown-object')
            elif e is ReadPropertyException:
                values = get_fault_obj_properties(reliability='rp-error')
            else:
                raise e

        properties.update(values)
        return properties

    def __put_device_end_to_verifier(self) -> None:
        """ device_id in queue means that device polled.
            Should send collected objects to HTTP
        """
        self.__verifier_queue.put(self.id)

    def __put_data_into_verifier(self, properties: dict) -> None:
        """ Send collected data about obj into BACnetVerifier
        """
        self.__verifier_queue.put(properties)

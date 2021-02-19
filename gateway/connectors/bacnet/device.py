from multiprocessing import SimpleQueue
from threading import Thread
from time import sleep, time

from BAC0.core.io.IOExceptions import (ReadPropertyException,
                                       NoResponseFromController,
                                       UnknownObjectError,
                                       UnknownPropertyError,
                                       ReadPropertyMultipleException
                                       )

from gateway.models import BACnetObj, ObjType, ObjProperty
from gateway.utils import get_fault_obj_properties
from gateway.utils import get_file_logger


class BACnetDevice(Thread):
    __slots__ = ('id', 'update_period', '_log', '_connector', '_verifier_queue',
                 'address', 'network', 'support_rpm', 'not_support_rpm',
                 '_active', '_polling'
                 )
    delay_inactive = 60  # todo move to cfg

    def __init__(self,
                 verifier_queue: SimpleQueue,
                 connector,
                 address: str,
                 device_id: int,
                 network,
                 objects: set[BACnetObj],
                 update_period: int):
        super().__init__()
        self.id = device_id
        self.setName(name=f'{self}-Thread')
        self.setDaemon(True)

        # todo config

        self.update_period = update_period

        self._log = get_file_logger(logger_name=f'{device_id}')

        self._connector = connector
        self._verifier_queue = verifier_queue

        self.address = address
        self.network = network

        self.support_rpm: set[BACnetObj] = objects
        self.not_support_rpm: set[BACnetObj] = set()

        # self.__objects_per_rpm = 25
        # todo: Should we use one RPM for several objects?

        self._active = True
        self._polling = True

        self._log.info(f'{self} starting ...')
        self.start()

    def __repr__(self):
        return f'{self.__class__.__name__}:[{self.id}]'

    def __len__(self):
        """ :return: the quantity of objects in the device received from the server
        """
        return len(self.support_rpm) + len(self.not_support_rpm)

    def run(self):
        while self._polling:
            self._log.debug('Polling started')
            if self._active:
                self._log.debug(f'{self} is active')
                try:
                    t0 = time()
                    self.poll()  # poll all objects
                    t1 = time()
                    time_delta = t1 - t0

                    self._log.info(
                        '\n==================================================\n'
                        f'{self} ip:{self.address} polled for: '
                        f'{round(time_delta, ndigits=2)} sec.\n'
                        f'Update period: {self.update_period} sec.\n'
                        f'Objects: {len(self)}\n'
                        f'Support RPM: {len(self.support_rpm)}\n'
                        f'Not support RPM: {len(self.not_support_rpm)}\n'
                        '==================================================')

                    self._log.info(
                        f'Timedelta = {time_delta}, upd_period = {self.update_period}')
                    if time_delta < self.update_period:
                        waiting_time = (self.update_period - time_delta) * 0.8
                        self._log.info(
                            f'{self} Sleeping {round(waiting_time, ndigits=2)} sec ...')
                        sleep(waiting_time)

                except Exception as e:
                    self._log.error(f'Polling error: {e}', exc_info=True)
            else:  # if device inactive
                self._log.debug(f'{self} is inactive')
                try:
                    device_obj = BACnetObj(type=ObjType.DEVICE,
                                           id=self.id,
                                           name='None'
                                           )
                    device_id = self.read_property(obj=device_obj,
                                                   prop=ObjProperty.objectIdentifier
                                                   )
                    self._log.info(f'PING: device_id: {device_id} <{type(device_id)}>')

                    if device_id:
                        self._log.debug(f'{self} setting to active ...')
                        self._active = True
                        continue
                except Exception as e:
                    self._log.error(f"'Ping checking' error: {e}")
                    pass
                # todo: close Thread and push to bacnet-connector
                self._log.debug(f'Sleeping {self.delay_inactive} sec ...')
                sleep(self.delay_inactive)  # todo from cfg
        else:
            self._log.info(f'{self} stopped.')

    def start_polling(self) -> None:
        self._polling = True
        self._log.info('Starting polling ...')
        self.start()

    def stop_polling(self) -> None:
        self._polling = False
        self._log.info('Stopping polling ...')

    def set_inactive(self) -> None:
        self._active = False
        self._log.warning(f'{self} switched to inactive.')
        # TODO put to bacnet connector for ping checking

    def poll(self) -> None:
        """ Poll all object from device.
        Send each object into verifier after response by protocol.
        When all objects polled, send device_id into verifier as finish signal
        """
        for obj in self.support_rpm:
            assert isinstance(obj, BACnetObj)

            self._log.debug(f'Polling supporting PRM {obj} ...')
            try:
                values = self.rpm(obj=obj)
                self._log.debug(f'{obj} values: {values}')
            except ReadPropertyMultipleException as e:
                self._log.warning(f'{obj} rpm error: {e}\n'
                                  f'{obj} Marking as not supporting RPM ...')
                self.not_support_rpm.add(obj)
                # self.support_rpm.discard(obj)

            except Exception as e:
                self._log.error(f'{obj} polling error: {e}', exc_info=True)
            else:
                self._log.debug(f'From {obj} read: {values}. Sending to verifier ...')
                self._put_data_into_verifier(properties=values)

        self.support_rpm.difference_update(self.not_support_rpm)

        for obj in self.not_support_rpm:
            assert isinstance(obj, BACnetObj)

            self._log.debug(f'Polling not supporting PRM {obj} ...')
            try:
                values = self.simulate_rpm(obj=obj)
            except UnknownObjectError as e:
                self._log.error(f'{obj} is unknown: {e}')
            except Exception as e:
                self._log.error(f'{obj} polling error: {e}', exc_info=True)
            else:
                self._log.debug(f'From {obj} read: {values}. Sending to verifier ...')
                self._put_data_into_verifier(properties=values)

        # notify verifier, that device polled and should send collected objects via HTTP
        self._log.debug('All objects were polled. Send device_id to verifier')
        self._put_device_end_to_verifier()

    def read_property(self, obj: BACnetObj, prop: ObjProperty):
        try:
            request = ' '.join([
                self.address,
                obj.type.name,
                str(obj.id),
                prop.name
            ])
            response = self.network.read_modbus(request)
        # except UnknownPropertyError:
        #     return self.__get_fault_obj_properties(reliability='unknown-property')
        # except UnknownObjectError:
        #     return self.__get_fault_obj_properties(reliability='unknown-object')
        # except NoResponseFromController:
        #     return self.__get_fault_obj_properties(reliability='no-response')
        except Exception as e:
            self._log.error(f'RP Error: {e}')
            raise e
            # return self.__get_fault_obj_properties(reliability='rp-error')
        else:
            if response is not None:
                if isinstance(response, str) and not response.strip():
                    raise ReadPropertyException('Response is empty')
                return response
            raise ReadPropertyException('Response is None')

    def read_property_multiple(self, obj: BACnetObj,
                               properties: list[ObjProperty]) -> dict:
        try:
            request = ' '.join([self.address,
                                obj.type.name,
                                str(obj.id),
                                *[prop.name for prop in properties]
                                ])
            response = self.network.readMultiple(request)

            # check values for None and empty strings
            values = {properties[i]: value for i, value in enumerate(response)
                      if value is not None and str(value).strip()}

        except Exception as e:
            self._log.warning(f'RPM Error: {e}')
            raise ReadPropertyMultipleException(e)
        else:
            if values is not None:
                return values
            else:
                raise ReadPropertyMultipleException('Response is None')

    def __simulate_rpm(self, obj: BACnetObj, properties: list[ObjProperty]) -> dict:
        values = {}
        for prop in properties:
            try:
                response = self.read_property(obj=obj, prop=prop)

            except (UnknownObjectError, NoResponseFromController) as e:
                self._log.warning(f'sRPM Error: {e}')
                raise e

            except (UnknownPropertyError, ReadPropertyException) as e:
                if prop is ObjProperty.priorityArray:
                    continue
                self._log.warning(f'sRPM Error: {e}')
                raise e
            except TypeError as e:
                self._log.error(f'Type error: {e}')
                raise e
            except Exception as e:
                self._log.error(f'sRPM error: {e}', exc_info=True)

            else:
                values.update({prop: response})
                # self.not_support_rpm.update(obj)

        return values

    def rpm(self, obj: BACnetObj) -> dict:
        properties = {
            ObjProperty.deviceId: self.id,
            ObjProperty.objectName: obj.name,
            ObjProperty.objectType: obj.type,
            ObjProperty.objectIdentifier: obj.id,
        }
        try:
            values = self.read_property_multiple(obj=obj,
                                                 properties=obj.type.properties
                                                 )

        except ReadPropertyMultipleException as e:
            self._log.error(f'Read Error: {e}')
            raise e
        else:
            properties.update(values)
            return properties

    def simulate_rpm(self, obj: BACnetObj) -> dict:
        properties = {
            ObjProperty.deviceId: self.id,
            ObjProperty.objectName: obj.name,
            ObjProperty.objectType: obj.type,
            ObjProperty.objectIdentifier: obj.id,
        }
        try:
            values = self.__simulate_rpm(obj=obj,
                                         properties=obj.type.properties
                                         )

        except NoResponseFromController as e:
            self._log.error(f'No response error: {e}')
            values = get_fault_obj_properties(reliability='no-response')
        except UnknownPropertyError as e:
            self._log.error(f'Unknown property error: {e}')
            values = get_fault_obj_properties(reliability='unknown-property')
        except UnknownObjectError as e:
            self._log.error(f'Unknown object error: {e}')
            values = get_fault_obj_properties(reliability='unknown-object')
        except (ReadPropertyException, TypeError) as e:
            self._log.error(f'RP error: {e}')
            values = get_fault_obj_properties(reliability='rp-error')
        except Exception as e:
            self._log.error(f'Read Error: {e}', exc_info=True)
            values = get_fault_obj_properties(reliability='error')
        finally:
            properties.update(values)
            return properties

    def _put_device_end_to_verifier(self) -> None:
        """device_id in queue means that device polled.
        Should send collected objects to HTTP.
        """
        self._verifier_queue.put(self.id)

    def _put_data_into_verifier(self, properties: dict) -> None:
        """Send collected data about obj into BACnetVerifier."""
        self._verifier_queue.put(properties)

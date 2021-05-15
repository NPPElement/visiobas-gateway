from multiprocessing import SimpleQueue
from pathlib import Path
from threading import Thread
from time import time, sleep

from pymodbus.bit_read_message import ReadBitsResponseBase
from pymodbus.client.sync import ModbusTcpClient
from pymodbus.register_read_message import ReadRegistersResponseBase

from gateway.connectors.bacnet import ObjProperty
from gateway.connectors.modbus import (ModbusObject,
                                       VisioModbusProperties,
                                       cast_to_bit,
                                       cast_2_registers)
from gateway.logs import get_file_logger


class ModbusTCPDevice(Thread):
    __slots__ = ('id', 'address', 'port', 'update_period', '__logger',
                 '__client', '__available_functions',
                 '__connector', '__verifier_queue',
                 '__polling', 'objects')

    def __init__(self,
                 verifier_queue: SimpleQueue,
                 connector,
                 address: str,
                 device_id: int,
                 objects: set[ModbusObject],
                 update_period: int = 10):
        super().__init__()

        self.id = device_id
        self.address, self.port = address.split(sep=':', maxsplit=1)
        self.update_period = update_period

        _base_path = Path(__file__).resolve().parent.parent.parent
        _log_file_path = _base_path / f'logs/{self.id}.log'

        self.__logger = get_file_logger(logger_name=f'{self}',
                                        size_bytes=50_000_000,
                                        file_path=_log_file_path)

        self.__client, self.__available_functions = None, None

        self.setName(name=f'{self}-Thread')
        self.setDaemon(True)

        self.__connector = connector
        self.__verifier_queue = verifier_queue

        self.__polling = True

        self.objects: set[ModbusObject] = objects

        self.__logger.info(f'{self} starting ...')
        self.start()

    def __len__(self):
        return len(self.objects)

    def stop_polling(self) -> None:
        self.__client.close()
        self.__polling = False
        self.__logger.info('Stopping polling ...')

    def run(self):
        while self.__polling:  # and self.__client.protocol is not None:
            if hasattr(self.__client, 'is_socket_open') and self.__client.is_socket_open():
                self.__logger.debug('Polling started')
                try:
                    t0 = time()
                    self.poll(objects=list(self.objects))
                    t1 = time()
                    time_delta = t1 - t0

                    self.__logger.info(
                        '\n==================================================\n'
                        f'{self} ip:{self.address} polled for: '
                        f'{round(time_delta, ndigits=2)} sec.\n'
                        f'Update period: {self.update_period} sec.\n'
                        f'Objects: {len(self)}\n'
                        '==================================================')

                    if time_delta < self.update_period:
                        waiting_time = (self.update_period - time_delta) * 0.8
                        self.__logger.debug(
                            f'{self} Sleeping {round(waiting_time, ndigits=2)} sec ...')
                        sleep(waiting_time)

                except Exception as e:
                    self.__logger.error(f'Polling error: {e}', exc_info=True)
            else:  # client not connect
                self.__logger.info('Connecting to client ...')
                try:
                    self.__client, self.__available_functions = self.__get_client(
                        address=self.address,
                        port=self.port)
                except ConnectionError as e:
                    self.__logger.error(f'{self} connection error: {e} '
                                        'Sleeping 60 sec to next attempt ...')
                    sleep(60)
                except Exception as e:
                    self.__logger.error(f'{self} initialization error: {e}', exc_info=True)
        else:
            self.__logger.info(f'{self} stopped.')

    def __repr__(self):
        return f'ModbusDevice [{self.id}]'

    def __get_client(self, address: str, port: int) -> tuple:
        """ Initialize modbus client
        """
        try:
            client = ModbusTcpClient(host=address,
                                     port=port,
                                     retries=5,
                                     retry_on_empty=True,
                                     retry_on_invalid=True)
            client.connect()
            available_functions = {
                1: client.read_coils,
                2: client.read_discrete_inputs,
                3: client.read_holding_registers,
                4: client.read_input_registers,
                5: client.write_coil,
                6: client.write_register,
                15: client.write_coils,
                16: client.write_registers
            }
            self.__logger.info(f'{self} client initialized')

        except Exception as e:
            self.__logger.error(f'Modbus client init error: {e}', exc_info=True)
            raise ConnectionError
        else:
            return client, available_functions

    def read(self, cmd_code: int, reg_address: int,
             quantity: int, unit=0x01) -> list[int] or None:
        """ Read data from Modbus registers
        """
        if cmd_code not in {1, 2, 3, 4}:
            raise ValueError('Read functions must be one of 1..4')

        try:
            data = self.__available_functions[cmd_code](address=reg_address,
                                                        count=quantity,
                                                        unit=unit)
        except Exception as e:
            self.__logger.error(
                f'Read error from reg: {reg_address}, quantity: {quantity} : {e}',
                exc_info=True)
            return None

        else:
            if not data.isError():
                if isinstance(data, ReadBitsResponseBase):
                    self.__logger.debug(
                        f'From register: {reg_address} read: {data.getBit(0)}')
                    return data.bits  # using one-bit registers
                elif isinstance(data, ReadRegistersResponseBase):
                    self.__logger.debug(
                        f'From register: {reg_address} read: {data.registers}')
                    return data.registers
            else:
                self.__logger.error(f'Received error response from {reg_address}')
                return None

    def process_registers(self, registers: list[int],
                          quantity: int,
                          properties: VisioModbusProperties) -> int or float or str:
        """ Perform casting to desired type and scale"""
        if registers is None:
            return 'null'

        data_type = properties.data_type.lower()

        if data_type == 'bool' and quantity == 1 and properties.data_length == 1:
            # bool: 1bit
            # TODO: Group bits into one request for BOOL
            value = 1 if registers[0] else 0
            # if registers is False:
            #     value = 0
            # elif registers is True:
            #     value = 1
            # else:
            #     value = cast_to_bit(register=registers, bit=properties.bit)

        elif (data_type == 'bool' and quantity == 1 and
              properties.data_length == 16):
            # bool: 16bit
            value = int(bool(registers[0]))

        elif quantity == 1 and properties.data_length == 16:
            # expected only: int16 | uint16 |  fixme: BYTE?
            value = registers[0]

        elif (data_type == 'float' and
              quantity == 2 and properties.data_length == 32):  # float32
            value = round(cast_2_registers(registers=registers,
                                           byteorder='>', wordorder='<',  # fixme use obj
                                           type_name=properties.data_type),
                          ndigits=6)
        elif ((data_type == 'int' or data_type == 'UINT') and
              quantity == 2 and properties.data_length == 32):  # int32 | uint32
            value = cast_2_registers(registers=registers,
                                     byteorder='<', wordorder='>',  # fixme use obj
                                     type_name=data_type)
        else:
            raise NotImplementedError('What to do with that type '
                                      f'not yet defined: {registers, quantity, properties}')
        scaled = value / properties.scale

        self.__logger.debug(
            f'Registers: {registers} Casted: {value} '
            f'scale: {properties.scale} scaled: {scaled} ')
        return scaled

    def poll(self, objects: list[ModbusObject]) -> None:
        """ Read objects from registers in Modbus Device.
            Convert register values to BACnet properties.
            Send convert objects into verifier.
            When all objects polled, send device_id into verifier as finish signal.
        """
        for obj in objects:
            try:
                registers = self.read(cmd_code=obj.func_read,
                                      reg_address=obj.address,
                                      quantity=obj.quantity
                                      )
                value = self.process_registers(registers=registers,
                                               quantity=obj.quantity,
                                               properties=obj.properties
                                               )
                converted_properties = self.__convert_to_bacnet_properties(
                    device_id=self.id,
                    obj=obj,
                    value=value
                )
                self.__put_data_into_verifier(properties=converted_properties)

            except Exception as e:
                self.__logger.warning(f'Object {obj} was skipped due to an error: {e}',
                                      exc_info=True)

        # [self.__put_data_into_verifier(
        #     self.__convert_to_bacnet_properties(
        #         device_id=self.id,
        #         obj=obj,
        #         value=self.process_registers(
        #             registers=self.read(
        #                 cmd_code=obj.func_read,
        #                 reg_address=obj.address,
        #                 quantity=obj.quantity),
        #             quantity=obj.quantity,
        #             properties=obj.properties)
        #     )) for obj in objects]

        self.__put_device_end_to_verifier()

    @staticmethod
    def __convert_to_bacnet_properties(device_id: int,
                                       obj: ModbusObject, value) -> dict[ObjProperty, ...]:
        """ Represent modbus register value as a bacnet object
        """
        return {
            ObjProperty.deviceId: device_id,
            ObjProperty.objectName: obj.name,
            ObjProperty.objectType: obj.type,
            ObjProperty.objectIdentifier: obj.id,
            ObjProperty.presentValue: value,
        }

    def __put_data_into_verifier(self, properties: dict) -> None:
        """ Send collected data about obj into BACnetVerifier
        """
        self.__verifier_queue.put(properties)

    def __put_device_end_to_verifier(self) -> None:
        """ device_id in queue means that device polled.
            Should send collected objects to HTTP
        """
        self.__verifier_queue.put(self.id)

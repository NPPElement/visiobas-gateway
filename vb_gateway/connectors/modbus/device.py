import asyncio
from multiprocessing import SimpleQueue
from pathlib import Path
from threading import Thread
from time import time, sleep
from typing import Set, List

from pymodbus.client.asynchronous.schedulers import ASYNC_IO
from pymodbus.client.asynchronous.tcp import AsyncModbusTCPClient

from vb_gateway.connectors.bacnet.obj_property import ObjProperty
from vb_gateway.connectors.modbus.object import ModbusObject
from vb_gateway.utility.utility import get_file_logger


class ModbusDevice(Thread):
    def __init__(self,
                 verifier_queue: SimpleQueue,
                 connector,
                 address: str,
                 device_id: int,
                 objects: Set[ModbusObject],
                 update_period: int = 10):
        super().__init__()

        __slots__ = ('id', 'address', 'port', 'update_period', '__logger',
                     '__loop', '__client', '__available_functions',
                     '__connector', '__verifier_queue',
                     '__active', '__polling',
                     'objects',)

        self.id = device_id
        self.address, self.port = address.split(sep=':', maxsplit=1)
        self.update_period = update_period

        base_path = Path(__file__).resolve().parent.parent.parent
        log_file_path = base_path / f'logs/{__name__}.log'

        self.__logger = get_file_logger(logger_name=f'{self}',
                                        file_size_bytes=50_000_000,
                                        file_path=log_file_path)

        self.__loop, self.__client = self.__set_client(address=self.address,
                                                       port=self.port)

        self.__available_functions = {
            1: self.__client.protocol.read_coils,
            2: self.__client.protocol.read_discrete_inputs,
            3: self.__client.protocol.read_holding_registers,
            4: self.__client.protocol.read_input_registers,
            5: self.__client.protocol.write_coil,
            6: self.__client.protocol.write_register,
            15: self.__client.protocol.write_coils,
            16: self.__client.protocol.write_registers,
        }

        self.setName(name=f'{self}-Thread')
        self.setDaemon(True)

        self.__connector = connector
        self.__verifier_queue = verifier_queue

        self.__active = True
        self.__polling = True

        self.objects: Set[ModbusObject] = objects

        self.__logger.info(f'{self} starting ...')
        self.start()

    def __len__(self):
        return len(self.objects)

    def stop_polling(self) -> None:
        self.__polling = False
        # self.__modbus_client.close()  # for sync client
        self.__logger.info('Stopping polling ...')

    def run(self):
        while self.__polling and self.__client:
            if self.__active:
                self.__logger.debug(f'{self} is active')
                try:
                    t0 = time()
                    self.__loop.run_until_complete(self.poll(objects=list(self.objects)))
                    t1 = time()
                    time_delta = t1 - t0

                    self.__logger.info(
                        '\n==================================================\n'
                        f'{self} ip:{self.address} polled '
                        f'for {round(time_delta, ndigits=2)} seconds\n'
                        f'Objects: {len(self)}\n'
                        '==================================================')

                    if time_delta < self.update_period:
                        waiting_time = self.update_period - time_delta
                        sleep(waiting_time)

                except Exception as e:
                    self.__logger.error(f'Polling error: {e}', exc_info=True)

    def __repr__(self):
        return f'ModbusDevice [{self.id}]'

    def __set_client(self, address: str, port: int) -> tuple:
        loop, modbus_client = AsyncModbusTCPClient(scheduler=ASYNC_IO,
                                                   host=address,
                                                   port=port)

        if modbus_client.protocol is not None and loop is not None:
            self.__logger.debug(f'Connected to {self}')
            return loop, modbus_client
        else:
            raise ConnectionError(f'Failed to connect to {self} '
                                  f'({self.address}:{self.port})')

    # def __set_client(self, address: str, port: int):
    #     client = ModbusTcpClient(host=address, port=port)
    #     if client.connect():
    #         self.__logger.debug(f'Connected to {self}')
    #         return client
    #     else:
    #         raise ConnectionError(f'Failed to connect to {self} '
    #                               f'({self.address}:{self.port})')

    async def read(self, cmd_code: int, reg_address: int,
                   quantity: int = 1, unit=0x01):
        """ Read data from Modbus registers
        """
        if cmd_code not in {1, 2, 3, 4}:
            raise ValueError('Read functions must be one from 1..4')
        try:
            data = await self.__available_functions[cmd_code](address=reg_address,
                                                              count=quantity,
                                                              unit=unit)
        except asyncio.TimeoutError as e:
            self.__logger.error(f'Read Timeout: {e}')
            return 'null'

        else:
            if not data.isError():
                self.__logger.debug(f'From register: {reg_address} read: {data.registers}')
                if quantity == 1:
                    return data.registers[0]
                return data.registers
            else:
                self.__logger.error(f'Received error response from {reg_address}')
                return 'null'

    async def poll(self, objects: List[ModbusObject]) -> None:
        """ Poll all objects for Modbus Device asynchronously.
            Send objects into verifier.
            When all objects polled, send device_id into verifier as finish signal.
        """
        obj_requests = [self.read(cmd_code=obj.func_read,
                                  reg_address=obj.address,
                                  quantity=obj.quantity) for obj in objects]
        values = await asyncio.gather(*obj_requests)

        assert len(values) == len(objects)

        for i in range(len(objects)):
            bacnet_properties = self.__convert_to_bacnet_properties(device_id=self.id,
                                                                    obj=objects[i],
                                                                    value=values[i])
            self.__put_data_into_verifier(properties=bacnet_properties)
        self.__put_device_end_to_verifier()

    @staticmethod
    def __convert_to_bacnet_properties(device_id: int,
                                       obj: ModbusObject, value) -> dict:
        """ Represent modbus register value as a bacnet object
        """
        # sf = StatusFlags()
        # if value is not None:
        # if isinstance(value, str) and not value.strip():
        # sf.set(fault=True)
        # else:
        # sf.set(fault=True)

        properties = {
            ObjProperty.deviceId: device_id,
            ObjProperty.objectName: obj.name,
            ObjProperty.objectType: obj.type,
            ObjProperty.objectIdentifier: obj.id,
            ObjProperty.presentValue: value,
            # ObjProperty.statusFlags: sf
        }
        return properties

    def __put_data_into_verifier(self, properties: dict) -> None:
        """ Send collected data about obj into BACnetVerifier
        """
        self.__verifier_queue.put(properties)

    def __put_device_end_to_verifier(self) -> None:
        """ device_id in queue means that device polled.
            Should send collected objects to HTTP
        """
        self.__verifier_queue.put(self.id)

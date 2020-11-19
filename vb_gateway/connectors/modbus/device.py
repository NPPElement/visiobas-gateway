import asyncio
from multiprocessing import SimpleQueue
from pathlib import Path
from threading import Thread
from time import time
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
                 objects: Set[ModbusObject]):
        super().__init__()

        self.id = device_id
        self.address, self.port = address.split(sep=':', maxsplit=1)
        self.__loop, self.__modbus_client = self.__set_client(address=self.address,
                                                              port=self.port)
        self.__available_functions = {
            1: self.__modbus_client.protocol.read_coils,
            2: self.__modbus_client.protocol.read_discrete_inputs,
            3: self.__modbus_client.protocol.read_holding_registers,
            4: self.__modbus_client.protocol.read_input_registers,
            5: self.__modbus_client.protocol.write_coil,
            6: self.__modbus_client.protocol.write_register,
            15: self.__modbus_client.protocol.write_coils,
            16: self.__modbus_client.protocol.write_registers,
        }

        base_path = Path(__file__).resolve().parent.parent.parent
        log_file_path = base_path / f'logs/{__name__}.log'

        self.__logger = get_file_logger(logger_name=f'{self}',
                                        file_size_bytes=50_000_000,
                                        file_path=log_file_path)

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
        self.__logger.info('Stopping polling ...')

    def run(self):
        while self.__polling and self.__modbus_client:
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
                except AssertionError:
                    self.__logger.error('Length of objects and values not equal',
                                        exc_info=True)
                except Exception as e:
                    self.__logger.error(f'Polling error: {e}', exc_info=True)

    def __repr__(self):
        return f'ModbusDevice [{self.id}]'

    def __set_client(self, address: str, port: int) -> tuple:
        loop, modbus_client = AsyncModbusTCPClient(scheduler=ASYNC_IO,
                                                   host=address,
                                                   port=port)

        if modbus_client.protocol is not None and loop is not None:
            return loop, modbus_client
        else:
            raise ConnectionError(f'Failed to connect to {self} '
                                  f'({self.address}:{self.port})')

    async def read(self, cmd_code: int, reg_address: int,
                   quantity: int = 1, units=0x01):
        """ Read data from Modbus registers
        """
        if cmd_code not in {1, 2, 3, 4}:
            raise ValueError('Read functions must be one of  1..4')

        data = await self.__available_functions[cmd_code](address=reg_address,
                                                          count=quantity,
                                                          units=units)
        if data.isError:
            return 'null'
        if quantity == 1:
            return data.registers[0]

        return data.registers

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

from multiprocessing import SimpleQueue
from threading import Thread
from time import time, sleep

from pymodbus.client.sync import ModbusTcpClient

from gateway.models import ModbusObj, VisioModbusProperties, ObjProperty
from gateway.utils import cast_to_bit
from logs import get_file_logger


class ModbusDevice(Thread):
    __slots__ = ('id', 'address', 'port', 'update_period', '_log',
                 '_client', '_available_functions',
                 '_connector', '_verifier_queue',
                 '_polling', 'objects'
                 )

    update_period_factor = 0.8
    before_next_client_attempt = 60

    def __init__(self,
                 verifier_queue: SimpleQueue,
                 connector,
                 address: str,
                 device_id: int,
                 objects: set[ModbusObj],
                 update_period: int = 10):
        super().__init__()
        self.setName(name=f'{self}-Thread')
        self.setDaemon(True)

        self.id = device_id
        self.address, self.port = address.split(sep=':', maxsplit=1)
        self.update_period = update_period

        self._log = get_file_logger(logger_name=f'{device_id}')

        self._client, self._available_functions = None, None

        self._connector = connector
        self._verifier_queue = verifier_queue

        self._polling = True

        self.objects: set[ModbusObj] = objects

        self._log.info(f'{self} starting ...')
        self.start()

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}[{self.id}]'

    def __len__(self) -> int:
        return len(self.objects)

    def stop_polling(self) -> None:
        self._client.close()
        self._polling = False
        self._log.info('Stopping polling ...')

    def run(self):
        while self._polling:  # and self.__client.protocol is not None:
            if hasattr(self._client, 'is_socket_open') and self._client.is_socket_open():
                self._log.debug('Polling started')
                try:
                    t0 = time()
                    self.poll(objects=list(self.objects))
                    t1 = time()
                    time_delta = t1 - t0

                    self._log.info(
                        '\n==================================================\n'
                        f'{self} ip:{self.address} polled for: '
                        f'{round(time_delta, ndigits=2)} sec.\n'
                        f'Update period: {self.update_period} sec.\n'
                        f'Objects: {len(self)}\n'
                        '==================================================')

                    if time_delta < self.update_period:
                        waiting_time = (self.update_period - time_delta) * \
                                       self.update_period_factor
                        self._log.debug(
                            f'{self} Sleeping {round(waiting_time, ndigits=2)} sec ...')
                        sleep(waiting_time)

                except Exception as e:
                    self._log.error(f'Polling error: {e}',
                                    exc_info=True
                                    )
            else:  # client not connect
                self._log.info('Connecting to client ...')
                try:
                    self._client, self._available_functions = self._get_client(
                        address=self.address,
                        port=self.port)
                except ConnectionError as e:
                    self._log.error(f'{self} connection error: {e} '
                                    'Sleeping 60 sec before next attempt ...')
                    sleep(self.before_next_client_attempt)
                except Exception as e:
                    self._log.error(f'{self} initialization error: {e}',
                                    exc_info=True
                                    )
        else:
            self._log.info(f'{self} stopped.')

    def _get_client(self, address: str, port: int) -> tuple:
        """ Initialize modbus client
        """
        try:
            client = ModbusTcpClient(host=address,
                                     port=port,
                                     retries=5,
                                     retry_on_empty=True,
                                     retry_on_invalid=True
                                     )
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
            self._log.info(f'{self} client initialized')
            return client, available_functions

        except Exception as e:
            self._log.error(f'Modbus client init error: {e}', exc_info=True)
            raise e

    def read(self, cmd_code: int, reg_address: int,
             quantity: int, unit=0x01) -> list:
        """Read data from Modbus registers."""
        read_cmd_codes = {1, 2, 3, 4}
        if cmd_code not in read_cmd_codes:
            raise ValueError(f'Read functions must be one of {read_cmd_codes}')

        # try:  # todo: do we need re-raise??
        data = self._available_functions[cmd_code](address=reg_address,
                                                   count=quantity,
                                                   unit=unit
                                                   )
        if not data.isError():
            self._log.debug(
                f'Successfully read: {reg_address}({quantity}): {data.registers}')
            return data.registers
        else:
            self._log.warning(f'Read failed: {data}')
            raise data

    def write(self, cmd_code: int, reg_address: int,
              values, unit=0x01) -> None:
        """Write data to Modbus registers."""
        write_cmd_codes = {5, 6, 15, 16}
        if cmd_code not in write_cmd_codes:
            raise ValueError(f'Read functions must be one of {write_cmd_codes}')

        rq = self._available_functions[cmd_code](reg_address,
                                                 values,
                                                 unit=unit
                                                 )
        if not rq.isError():
            self._log.debug(f'Successfully write: {reg_address}: {values}')
        else:
            self._log.warning(f'Write failed: {rq}')
            raise rq

    def process_registers(self, registers: list[int],
                          quantity: int,
                          properties: VisioModbusProperties) -> int or float or str:
        """ Perform casting to desired type and scale"""
        if registers is None:
            return 'null'

        if (properties.data_type == 'BOOL' and quantity == 1 and
                properties.data_length == 1 and isinstance(properties.bit, int)):
            # bool: 1bit
            # TODO: Group bits into one request for BOOL
            value = cast_to_bit(register=registers, bit=properties.bit)

        elif (properties.data_type == 'BOOL' and quantity == 1 and
              properties.data_length == 16):
            # bool: 16bit
            value = int(bool(registers[0]))

        elif quantity == 1 and properties.data_length == 16:
            # expected only: int16 | uint16 |  fixme: BYTE?
            value = registers[0]

        # todo
        # elif (properties.data_type == 'FLOAT' and
        #       quantity == 2 and properties.data_length == 32):  # float32
        #     value = round(cast_2_registers(registers=registers,
        #                                    byteorder='>', wordorder='<',  # fixme use obj
        #                                    type_name=properties.data_type),
        #                   ndigits=6)
        # elif ((properties.data_type == 'INT' or properties.data_type == 'UINT') and
        #       quantity == 2 and properties.data_length == 32):  # int32 | uint32
        #     value = cast_2_registers(registers=registers,
        #                              byteorder='<', wordorder='>',  # fixme use obj
        #                              type_name=properties.data_type)
        else:
            raise NotImplementedError('What to do with that type '
                                      f'not yet defined: {registers, quantity, properties}')
        scaled = value / properties.scale

        self._log.debug(
            f'Registers: {registers} Casted: {value} '
            f'scale: {properties.scale} scaled: {scaled} ')
        return scaled

    def poll(self, objects: list[ModbusObj]) -> None:
        """ Read objects from registers in Modbus Device.
            Convert register values to BACnet properties.
            Send convert objects into verifier.
            When all objects polled, send device_id into verifier as finish signal.
        """
        for obj in objects:
            try:
                registers = self.read(cmd_code=obj.properties.func_read,
                                      reg_address=obj.properties.address,
                                      quantity=obj.properties.quantity
                                      )
                value = self.process_registers(registers=registers,
                                               quantity=obj.properties.quantity,
                                               properties=obj.properties
                                               )
                converted_properties = self._add_bacnet_properties(
                    device_id=self.id,
                    obj=obj,
                    value=value
                )
                self._put_data_into_verifier(properties=converted_properties)

            except Exception as e:
                self._log.warning(f'Read from {obj} error: {e}',
                                  exc_info=True
                                  )
                # todo: except read errors and add to reliability
                # todo: put obj data to verifier
        self._put_device_end_to_verifier()

    @staticmethod
    def _add_bacnet_properties(device_id: int,
                               obj: ModbusObj, value) -> dict[ObjProperty, ...]:
        """Represent modbus register value as a bacnet object."""
        return {ObjProperty.deviceId: device_id,
                ObjProperty.objectName: obj.name,
                ObjProperty.objectType: obj.type,
                ObjProperty.objectIdentifier: obj.id,
                ObjProperty.presentValue: value,
                }

    def _put_data_into_verifier(self, properties: dict) -> None:
        """Send collected data about obj into BACnetVerifier."""
        self._verifier_queue.put(properties)

    def _put_device_end_to_verifier(self) -> None:
        """device_id in queue means that device polled.
        Should send collected objects to HTTP
        """
        self._verifier_queue.put(self.id)

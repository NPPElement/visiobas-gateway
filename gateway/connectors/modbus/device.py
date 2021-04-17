# from logging import getLogger
# from multiprocessing import SimpleQueue
# from threading import Thread
# from time import time, sleep
# from typing import Iterable
#
# from pymodbus.client.sync import ModbusTcpClient
#
# from ...models import ModbusObjModel, MODBUS_READ_FUNCTIONS, ModbusFunc, \
#     MODBUS_WRITE_FUNCTIONS
#
#
# class ModbusDevice(Thread):
#     __slots__ = ['id', 'address', 'port', 'update_period', '_log',
#                  '_client', '_available_functions',
#                  '_connector', '_verifier_queue',
#                  '_polling', 'objects',
#                  ]
#
#     update_period_factor = 0.8
#     before_next_client_attempt = 60
#
#     def __init__(self,
#                  verifier_queue: SimpleQueue,
#                  connector,
#                  address: str,
#                  device_id: int,
#                  objects: set[ModbusObjModel],
#                  update_period: int = 10):
#         super().__init__()
#         self.id = device_id
#         self.setName(name=f'{self}-Thread')
#         self.setDaemon(True)
#
#         self.address, self.port = address.split(sep=':', maxsplit=1)
#         self.update_period = update_period
#
#         self._log = getLogger(name=f'{device_id}')
#
#         self._client, self._available_functions = None, None
#
#         self._connector = connector
#         self._verifier_queue = verifier_queue
#
#         self._polling = True
#
#         self.objects: set[ModbusObjModel] = objects
#
#         self._log.info(f'{self} starting ...')
#         # self.start()
#
#     def __repr__(self) -> str:
#         return f'{self.__class__.__name__}[{self.id}]'
#
#     def __len__(self) -> int:
#         return len(self.objects)
#
#     def stop_polling(self) -> None:
#         self._client.close()
#         self._polling = False
#         self._log.info('Stopping polling ...')
#
#     def run(self):
#         while self._polling:  # and self.__client.protocol is not None:
#             if hasattr(self._client, 'is_socket_open') and self._client.is_socket_open():
#                 self._log.debug('Polling started')
#                 try:
#                     t0 = time()
#                     self.poll(objects=list(self.objects))
#                     t1 = time()
#                     time_delta = t1 - t0
#
#                     self._log.info(
#                         '\n==================================================\n'
#                         f'{self} ip:{self.address} polled for: '
#                         f'{round(time_delta, ndigits=2)} sec.\n'
#                         f'Update period: {self.update_period} sec.\n'
#                         f'Objects: {len(self)}\n'
#                         '==================================================')
#
#                     if time_delta < self.update_period:
#                         waiting_time = (self.update_period - time_delta) * \
#                                        self.update_period_factor
#                         self._log.debug(
#                             f'{self} Sleeping {round(waiting_time, ndigits=2)} sec ...')
#                         sleep(waiting_time)
#
#                 except Exception as e:
#                     self._log.error(f'Polling error: {e}',
#                                     exc_info=True
#                                     )
#             else:  # client not connect
#                 self._log.info('Connecting to client ...')
#                 try:
#                     self._client, self._available_functions = self._get_client(
#                         address=self.address,
#                         port=self.port)
#                 except ConnectionError as e:
#                     self._log.error(f'{self} connection error: {e} '
#                                     'Sleeping 60 sec before next attempt ...')
#                     sleep(self.before_next_client_attempt)
#                 except Exception as e:
#                     self._log.error(f'{self} initialization error: {e}',
#                                     exc_info=True
#                                     )
#         else:
#             self._log.info(f'{self} stopped.')
#
#     def _get_client(self, address: str, port: int) -> tuple:
#         """ Initialize modbus client
#         """
#         try:
#             client = ModbusTcpClient(host=address,
#                                      port=port,
#                                      retries=5,
#                                      retry_on_empty=True,
#                                      retry_on_invalid=True
#                                      )
#             client.connect()
#             available_functions = {
#                 ModbusFunc.READ_COILS: client.read_coils,
#                 ModbusFunc.READ_DISCRETE_INPUTS: client.read_discrete_inputs,
#                 ModbusFunc.READ_HOLDING_REGISTERS: client.read_holding_registers,
#                 ModbusFunc.READ_INPUT_REGISTERS: client.read_input_registers,
#
#                 ModbusFunc.WRITE_COIL: client.write_coil,
#                 ModbusFunc.WRITE_REGISTER: client.write_register,
#                 ModbusFunc.WRITE_COILS: client.write_coils,
#                 ModbusFunc.WRITE_REGISTERS: client.write_registers
#             }
#             self._log.info(f'{self} client initialized')
#             return client, available_functions
#
#         except Exception as e:
#             self._log.error(f'Modbus client init error: {e}', exc_info=True)
#             raise e
#
#     def read(self, obj: ModbusObjModel, unit=0x01) -> list:
#         """Read data from Modbus registers."""
#
#         func_read = obj.property_list.func_read
#
#         if func_read not in MODBUS_READ_FUNCTIONS:
#             raise ValueError(f'Read functions must be one of {MODBUS_READ_FUNCTIONS}')
#
#         address = obj.property_list.address
#         quantity = obj.property_list.quantity
#
#         # try:  # todo: do we need re-raise??
#         data = self._available_functions[func_read](address=address,
#                                                     count=quantity,
#                                                     unit=unit
#                                                     )
#         if not data.isError():
#             self._log.debug(
#                 f'Successful reading {func_read} address={address} '
#                 f'quantity={quantity} registers={data.registers}'
#                 # extra={'cmd_code': cmd_code,
#                 #        'address': reg_address,
#                 #        'quantity': data.registers
#                 #        }
#             )
#             return data.registers
#         else:
#             # self._log.warning(f'Read failed: {data}')
#             raise ValueError(data)
#
#     def write(self, values, obj: ModbusObjModel, unit=0x01) -> None:
#         """Write data to Modbus registers."""
#
#         func_write = obj.property_list.func_write
#         reg_address = obj.property_list.address
#
#         if func_write not in MODBUS_WRITE_FUNCTIONS:
#             raise ValueError(f'Read functions must be one of {MODBUS_WRITE_FUNCTIONS}')
#
#         rq = self._available_functions[func_write](reg_address,
#                                                    values,
#                                                    unit=unit
#                                                    )
#         if not rq.isError():
#             self._log.debug(f'Successfully write: {reg_address}: {values}')
#         else:
#             self._log.warning(f'Write failed: {rq}')
#             raise rq
#
#     # def process_registers(self, registers: list[int],
#     #                       quantity: int,
#     #                       properties: VisioModbusProperties) -> int or float or str:
#     #     """ Perform casting to desired type and scale"""
#     #     if registers is None:
#     #         return 'null'
#     #
#     #     if (properties.data_type == 'BOOL' and quantity == 1 and
#     #             properties.data_length == 1 and isinstance(properties.bit, int)):
#     #         # bool: 1bit
#     #         # TODO: Group bits into one request for BOOL
#     #         value = cast_to_bit(register=registers, bit=properties.bit)
#     #
#     #     elif (properties.data_type == 'BOOL' and quantity == 1 and
#     #           properties.data_length == 16):
#     #         # bool: 16bit
#     #         value = int(bool(registers[0]))
#     #
#     #     elif quantity == 1 and properties.data_length == 16:
#     #         # expected only: int16 | uint16 |  fixme: BYTE?
#     #         value = registers[0]
#     #
#     #     # todo
#     #     elif (properties.data_type == 'FLOAT' and
#     #           quantity == 2 and properties.data_length == 32):  # float32
#     #         value = round(cast_2_registers(registers=registers,
#     #                                        data_len=properties.data_length,
#     #                                        byteorder='>', wordorder='<',  # fixme use obj
#     #                                        type_name=properties.data_type
#     #                                        ),
#     #                       ndigits=6)
#     #
#     #     # elif ((properties.data_type == 'INT' or properties.data_type == 'UINT') and
#     #     #       quantity == 2 and properties.data_length == 32):  # int32 | uint32
#     #     #     value = cast_2_registers(registers=registers,
#     #     #                              byteorder='<', wordorder='>',  # fixme use obj
#     #     #                              type_name=properties.data_type)
#     #     else:
#     #         raise NotImplementedError('What to do with that type '
#     #                                   f'not yet defined: {registers, quantity, properties}')
#     #     scaled = value / properties.scale
#     #
#     #     self._log.debug(f'Processed registers={registers} quantity={quantity} '
#     #                     f'properties={properties} cast_value={value} scaled_value={scaled}',
#     #                     # extra={'registers': registers,
#     #                     #        'quantity': quantity,
#     #                     #        'properties': properties,
#     #                     #        'cast value': value,
#     #                     #        'scaled': scaled,
#     #                     #        }
#     #                     )
#     #     return scaled
#
#     def poll(self, objects: Iterable[ModbusObjModel]) -> None:
#         """ Read objects from registers in Modbus Device.
#             Convert register values to BACnet properties.
#             Send convert objects into verifier.
#             When all objects polled, send device_id into verifier as finish signal.
#         """
#         for obj in objects:
#             try:
#                 registers = self.read(obj=obj)
#                 # todo: make process in read
#                 # value = self.process_registers(registers=registers,
#                 #                                quantity=obj.properties.quantity,
#                 #                                properties=obj.properties
#                 #                                )
#                 # todo: make by default
#                 # converted_properties = self._add_bacnet_properties(
#                 #     device_id=self.id,
#                 #     obj=obj,
#                 #     value=value
#                 # )
#                 # todo: put obj
#                 # self._put_data_into_verifier(properties=converted_properties)
#
#             except Exception as e:
#                 self._log.warning(f'Read from {obj} error: {e}',
#                                   exc_info=True
#                                   )
#                 # todo: except read errors and add to reliability
#                 # FIXME: put obj data to verifier
#         self._put_device_end_to_verifier()
#
#     # @staticmethod
#     # def _add_bacnet_properties(device_id: int,
#     #                            obj: ModbusObj, value) -> dict[ObjProperty, ...]:
#     #     """Represent modbus register value as a bacnet object."""
#     #     return {ObjProperty.deviceId: device_id,
#     #             ObjProperty.objectName: obj.name,
#     #             ObjProperty.objectType: obj.type,
#     #             ObjProperty.objectIdentifier: obj.id,
#     #             ObjProperty.presentValue: value,
#     #             }
#
#     def _put_data_into_verifier(self, obj: ModbusObjModel) -> None:
#         """Send collected data about obj into BACnetVerifier."""
#         self._verifier_queue.put(obj.dict(include={'device_id',
#                                                    'type'
#                                                    'id',
#                                                    'name'
#                                                    'present_value'
#                                                    }))
#
#     def _put_device_end_to_verifier(self) -> None:
#         """device_id in queue means that device polled.
#         Should send collected objects to HTTP
#         """
#         self._verifier_queue.put(self.id)

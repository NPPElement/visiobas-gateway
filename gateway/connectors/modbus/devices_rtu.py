# NOTE: LOW QUALITY CODE FOR 1.0.0 VERSION (OLD)

from multiprocessing import SimpleQueue
from pathlib import Path
from threading import Thread
from time import sleep, time

from pymodbus.client.sync import ModbusSerialClient
from pymodbus.constants import Defaults

from gateway.connectors import ObjProperty
from gateway.connectors.modbus import ModbusObject, cast_2_registers, cast_to_bit, \
    VisioModbusProperties
from gateway.logs import get_file_logger


class ModbusRTUDevice(Thread):
    poll_period_factor = 0.8
    before_next_client_attempt = 60

    def __init__(self,
                 verifier_queue: SimpleQueue,
                 connector,
                 device_id: int,
                 objects: set[ModbusObject],
                 poll_period: int = 10,
                 **kwargs
                 ):
        super().__init__()
        self.id = device_id
        self.port = kwargs.get('port', 0)
        self.setName(name=f'{self}-Thread')
        self.setDaemon(True)

        _base_path = Path(__file__).resolve().parent.parent.parent
        _log_file_path = _base_path / f'logs/{self.port}.log'
        self._log = get_file_logger(logger_name=f'{self}',
                                    size_bytes=50_000_000,
                                    file_path=_log_file_path)

        self._verifier_queue = verifier_queue
        self._connector = connector

        self.method = 'rtu'

        self.baudrate = kwargs.get('baudrate', Defaults.Baudrate)
        # self.
        unit = kwargs.get('unit', 0)

        self.unit_id_mapping = {unit: self.id}

        self.stopbits = kwargs.get('stopbits', Defaults.Stopbits)
        self.bytesize = kwargs.get('bytesize', Defaults.Bytesize)
        self.parity = kwargs.get('parity', Defaults.Parity)
        self.timeout = kwargs.get('timeout', Defaults.Timeout)
        self.strict = kwargs.get("strict", False)

        # self.objects = objects
        self.objects: dict[int, set[ModbusObject]] = {unit: objects}

        self.poll_period = poll_period

        self._polling = True
        self.client = None
        self.available_functions = {}

        self.start()

    def get_device_id(self, unit: int) -> int:
        """Returns device id by unit."""
        return self.unit_id_mapping[unit]

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}[{self.port}]'

    def __len__(self) -> int:
        return len(self.objects)

    def add_objects(self, unit: int, objs: set[ModbusObject], dev_id: int) -> None:
        self.objects[unit] = objs
        self.unit_id_mapping[unit] = dev_id

    def _init_client(self, **kwargs) -> tuple or None:
        try:
            client = ModbusSerialClient(  # method=self.method,
                # port=self.port,
                # baudrate=self.baudrate,
                **kwargs
            )
            if not client.connect():
                raise ConnectionError('Cannot connect')
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

    def run(self) -> None:
        self._log.info(f'{self} starting ...')
        while self._polling:
            try:
                if self.client is not None:
                    self._log.debug('Polling started')
                    _t0 = time()
                    for unit_, objs in self.objects.items():
                        self.poll(objects=objs, unit=unit_)

                    _t_delta = time() - _t0
                    self._log.info('\n==================================================\n'
                                   f'{self} polled for: '
                                   f'{round(_t_delta, ndigits=1)} sec.\n'
                                   f'Update period: {self.poll_period} sec.\n'
                                   f'Objects: {len(self)}\n'
                                   )
                    if _t_delta < self.poll_period:
                        _delay = (self.poll_period - _t_delta) * self.poll_period_factor
                        self._log.debug(f'Sleeping {round(_delay, ndigits=1)} sec ...')
                        sleep(_delay)

                else:
                    self._log.info('Connecting to client ...')
                    try:
                        self.client, self.available_functions = self._init_client(
                            method=self.method,
                            port=self.port,
                            baudrate=self.baudrate,
                            stopbits=self.stopbits,
                            bytesize=self.bytesize,
                            parity=self.parity,
                            timeout=self.timeout,
                            strict=self.strict
                        )
                    except Exception as e:
                        self._log.warning(f'{self} connection error: {e} '
                                          'Sleeping 60 sec before next attempt ...')
                        sleep(self.before_next_client_attempt)
            except Exception as e:
                self._log.error(f'Polling error: {e}', exc_info=True)
        else:
            self._log.info(f'{self} stopped.')

    def poll(self, objects: set[ModbusObject], unit: int) -> None:
        for obj in objects:
            try:
                registers = self.read(obj=obj, unit=unit)
                value = self.process_registers(registers=registers,
                                               quantity=obj.quantity,
                                               properties=obj.properties)
                converted_properties = self._add_bacnet_properties(
                    device_id=self.get_device_id(unit=unit),
                    obj=obj,
                    value=value
                    )
                self._verifier_queue.put(converted_properties)
            except Exception as e:
                self._log.warning(f'Object {obj} was skipped due to an error: {e}',
                                  exc_info=True)
        # device_id in queue means that device polled.
        self._verifier_queue.put(self.get_device_id(unit=unit))
        self._log.info(f'Device UNIT={unit} polled')

    def stop_polling(self) -> None:
        self.client.close()
        self._polling = False
        self._log.info('Stopping polling ...')

    def read(self, obj: ModbusObject, unit: int) -> list:
        """Read data from Modbus object."""
        read_cmd_codes = {1, 2, 3, 4}

        read_cmd_code = obj.func_read
        if read_cmd_code not in read_cmd_codes:
            raise ValueError(f'Read functions must be one of {read_cmd_codes}')
        address = obj.address
        quantity = obj.quantity
        data = self.available_functions[read_cmd_code](address=address,
                                                       count=quantity,
                                                       unit=unit
                                                       )
        if not data.isError():
            self._log.debug(
                f'Successful reading UNIT={unit} address={address} '
                f'quantity={quantity} registers={data.registers}'
                # extra={'cmd_code': cmd_code,
                #        'address': reg_address,
                #        'quantity': data.registers
                #        }
            )
            return data.registers
        else:
            self._log.warning(f'Read failed: {data} UNIT={unit} {obj}')
            # raise ValueError(data)

    def write(self, values, obj: ModbusObject, unit: int) -> bool:
        """Write data to Modbus object."""
        write_cmd_codes = {5, 6, 15, 16}

        write_cmd_code = obj.func_write  # fixme parse from data
        if write_cmd_code not in write_cmd_codes:
            raise ValueError(f'Read functions must be one of {write_cmd_codes}')
        reg_address = obj.address

        rq = self.available_functions[write_cmd_code](reg_address,
                                                      values,
                                                      unit=unit
                                                      )
        if not rq.isError():
            self._log.debug(f'Successfully write: {reg_address}: {values}')
            return True
        else:
            self._log.warning(f'Write failed: {rq}')
            return False

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

        elif (properties.data_type == 'FLOAT' and
              quantity == 2 and properties.data_length == 32):  # float32
            value = round(cast_2_registers(registers=registers,
                                           byteorder='>', wordorder='<',  # fixme use obj
                                           type_name=properties.data_type),
                          ndigits=6)
        elif ((properties.data_type == 'INT' or properties.data_type == 'UINT') and
              quantity == 2 and properties.data_length == 32):  # int32 | uint32
            value = cast_2_registers(registers=registers,
                                     byteorder='<', wordorder='>',  # fixme use obj
                                     type_name=properties.data_type)
        else:
            raise NotImplementedError('What to do with that type '
                                      f'not yet defined: {registers, quantity, properties}')
        scaled = value / properties.scale

        self._log.debug(f'Registers: {registers} Casted: {value} '
                        f'scale: {properties.scale} scaled: {scaled} ')
        return scaled

    @staticmethod
    def _add_bacnet_properties(device_id: int,
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

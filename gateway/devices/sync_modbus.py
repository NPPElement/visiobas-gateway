import struct
from typing import Union, Any, Callable, Optional, Collection

from pymodbus.client.sync import ModbusSerialClient, ModbusTcpClient
from pymodbus.exceptions import ModbusException, ModbusIOException
from pymodbus.framer.rtu_framer import ModbusRtuFramer

from .base_modbus import BaseModbusDevice
from ..models import (BACnetDeviceObj, Protocol, ModbusReadFunc, ModbusWriteFunc, ModbusObj,
                      StatusFlags)

# aliases # TODO
# BACnetDeviceModel = Any  # ...models
VisioBASGateway = Any  # ...gateway_loop


class SyncModbusDevice(BaseModbusDevice):
    def __init__(self, device_obj: BACnetDeviceObj, gateway: VisioBASGateway):
        super().__init__(device_obj, gateway)
        self._client: Union[ModbusSerialClient, ModbusTcpClient] = None

    async def create_client(self) -> None:
        """Initializes synchronous modbus client."""

        self._LOG.debug('Creating pymodbus client', extra={'device_id': self.id})
        try:
            if self.protocol in {Protocol.MODBUS_TCP, Protocol.MODBUS_RTUOVERTCP}:
                framer = ModbusRtuFramer if self.protocol is Protocol.MODBUS_RTUOVERTCP else None
                self._client = ModbusTcpClient(host=str(self.address), port=self.port,
                                               framer=framer, retries=self.retries,
                                               retry_on_empty=True, retry_on_invalid=True,
                                               timeout=self.timeout)
            elif self.protocol is Protocol.MODBUS_RTU:
                if not self._serial_clients.get(self.serial_port):
                    self._LOG.debug('Serial port not using. Creating sync client',
                                    extra={'device_id': self.id,
                                           'serial_port': self.serial_port, })
                    self._client = ModbusSerialClient(method='rtu',
                                                      port=self.serial_port,
                                                      baudrate=self._device_obj.baudrate,
                                                      bytesize=self._device_obj.bytesize,
                                                      parity=self._device_obj.parity,
                                                      stopbits=self._device_obj.stopbits,
                                                      timeout=self.timeout)
                    self._serial_clients.update({self.serial_port: self._client})
                else:
                    self._LOG.debug('Serial port already using. Getting client',
                                    extra={'device_id': self.id,
                                           'serial_port': self.serial_port, })
                    self._client = self._serial_clients[self.serial_port]
            else:
                raise NotImplementedError('Other methods not support yet')

        except ModbusException as e:
            self._LOG.warning('Cannot create client',
                              extra={'device_id': self.id, 'exc': e, })
        else:
            self._connected = self._client.connect()
            self._LOG.debug('Client created', extra={'device_id': self.id})

    def close_client(self) -> None:
        self._client.close()
        if self.protocol is Protocol.MODBUS_RTU:
            self.__class__._serial_clients.pop(self.serial_port)
            self.__class__._serial_port_locks.pop(self.serial_port)

    @property
    def is_client_connected(self) -> bool:
        return self._connected

    @property
    def read_funcs(self) -> dict[ModbusReadFunc, Callable]:
        return {ModbusReadFunc.READ_COILS: self._client.read_coils,
                ModbusReadFunc.READ_DISCRETE_INPUTS: self._client.read_discrete_inputs,
                ModbusReadFunc.READ_HOLDING_REGISTERS: self._client.read_holding_registers,
                ModbusReadFunc.READ_INPUT_REGISTERS: self._client.read_input_registers,
                }

    @property
    def write_funcs(self) -> dict[ModbusWriteFunc, Callable]:
        return {ModbusWriteFunc.WRITE_COIL: self._client.write_coil,
                ModbusWriteFunc.WRITE_REGISTER: self._client.write_register,
                ModbusWriteFunc.WRITE_COILS: self._client.write_coils,
                ModbusWriteFunc.WRITE_REGISTERS: self._client.write_registers,
                }

    async def read(self, obj: ModbusObj, **kwargs) -> Optional[Union[int, float]]:
        await self._polling.wait()
        return await self._gateway.async_add_job(self.sync_read, obj)

    def sync_read(self, obj: ModbusObj) -> Optional[Union[int, float]]:
        """Read data from Modbus object.

        Updates object and return value.
        """
        try:
            if obj.func_read is ModbusReadFunc.READ_FILE:
                raise ModbusException('func-not-support')  # todo: implement 0x14 func
            resp = self.read_funcs[obj.func_read](address=obj.address,
                                                  count=obj.quantity,
                                                  unit=self.unit)
            if resp.isError():
                raise ModbusIOException('0x80')  # todo: resp.string

            value = self._decode_response(resp=resp, obj=obj)

            obj.set_pv(value=value)
            obj.sf = StatusFlags()
            obj.reliability = None
        except (TypeError, ValueError, AttributeError,
                ModbusException, Exception) as e:
            obj.set_exc(exc=e)
            self._LOG.warning('Read error',
                              extra={'device_id': self.id, 'object_id': obj.id,
                                     'object_type': obj.type, 'register': obj.address,
                                     'quantity': obj.quantity, 'exc': e,
                                     'unreachable_in_row': obj.unreachable_in_row, })
        # except Exception as e:
        #     obj.exception = e
        #     self._LOG.exception(f'Unexpected read error: {e}',
        #                         extra={'device_id': self.id, 'object_id': obj.id,
        #                                'object_type': obj.type, 'register': obj.address,
        #                                'quantity': obj.quantity, 'exc': e, })
        else:
            return obj.pv  # return not used now. Updates object

    async def write(self, value: Union[int, float], obj: ModbusObj, **kwargs) -> None:
        await self._gateway.async_add_job(self.sync_write, value, obj)

    def sync_write(self, value: Union[int, float], obj: ModbusObj) -> None:
        """Write value to Modbus object.

        Args:
            value: Value to write
            obj: Object instance.
        """
        try:
            if obj.func_write is None:
                raise ModbusException('Object cannot be overwritten')

            payload = self._build_payload(value=value, obj=obj)

            if (
                    obj.func_write is ModbusWriteFunc.WRITE_REGISTER
                    and isinstance(payload, list)
            ):
                # FIXME: hotfix
                assert len(payload) == 1
                payload = payload[0]

            rq = self.write_funcs[obj.func_write](obj.address, payload, unit=self.unit)
            if rq.isError():
                raise ModbusIOException('0x80')  # todo: resp.string
            self._LOG.debug(f'Successfully write',
                            extra={'device_id': self.id, 'object_id': obj.id,
                                   'object_type': obj.type, 'address': obj.address,
                                   'value': value, })
        except (ModbusException, struct.error, Exception) as e:
            self._LOG.warning('Failed write',
                              extra={'device_id': self.id, 'object_id': obj.id,
                                     'object_type': obj.type, 'register': obj.address,
                                     'quantity': obj.quantity, 'exc': e, })
        # except Exception as e:
        #     self._LOG.exception('Unhandled error',
        #                         extra={'device_id': self.id, 'object_id': obj.id,
        #                                'object_type': obj.type, 'register': obj.address,
        #                                'quantity': obj.quantity, 'exc': e, })

    async def _poll_objects(self, objs: Collection[ModbusObj]) -> None:
        # def _sync_poll_objects(objs_: Collection[ModbusObj]) -> None:
        #     for obj in objs_:
        #         self.sync_read(obj=obj)
        #
        # await self._gateway.async_add_job(_sync_poll_objects, objs)
        for obj in objs:
            await self.read(obj=obj)

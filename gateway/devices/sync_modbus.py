import asyncio
from typing import TYPE_CHECKING, Any, Callable, Collection, Optional, Union

from pymodbus.client.sync import ModbusSerialClient, ModbusTcpClient  # type: ignore
from pymodbus.exceptions import ModbusException, ModbusIOException  # type: ignore
from pymodbus.framer.rtu_framer import ModbusRtuFramer  # type: ignore
from pymodbus.framer.socket_framer import ModbusSocketFramer  # type: ignore

from ..models import (
    BACnetDeviceObj,
    BACnetObj,
    ModbusObj,
    ModbusReadFunc,
    ModbusWriteFunc,
    Protocol,
)
from ..utils import log_exceptions
from .base_modbus import BaseModbusDevice

if TYPE_CHECKING:
    from ..gateway_ import Gateway
else:
    Gateway = "Gateway"


class ModbusDevice(BaseModbusDevice):
    """Sync Modbus Device.

    Note: AsyncModbusDevice in `pymodbus` didn't work correctly. So support only Sync
        client.
    """

    def __init__(self, device_obj: BACnetDeviceObj, gateway: Gateway):
        super().__init__(device_obj, gateway)
        self._client: Union[ModbusSerialClient, ModbusTcpClient] = None  # type: ignore

    @log_exceptions
    def create_client(self) -> None:
        """Initializes synchronous modbus client."""

        self._LOG.debug("Creating pymodbus client", extra={"device_id": self.device_id})
        if self.protocol in {Protocol.MODBUS_TCP, Protocol.MODBUS_RTUOVERTCP}:
            framer = (
                ModbusRtuFramer
                if self.protocol is Protocol.MODBUS_RTUOVERTCP
                else ModbusSocketFramer
            )
            self._client = ModbusTcpClient(
                host=str(self.address),
                port=self.port,
                framer=framer,
                retries=self.retries,
                retry_on_empty=True,
                retry_on_invalid=True,
                timeout=self.timeout,
            )
            self._connected = self._client.connect()
            self._LOG.debug(
                "Client created",
                extra={
                    "device_id": self.device_id,
                },
            )
        elif self.protocol is Protocol.MODBUS_RTU:
            if self.serial_port is None:
                raise ValueError("Serial port required")
            if not self._serial_clients.get(self.serial_port):
                self._LOG.debug(
                    "Serial port not using. Creating sync client",
                    extra={
                        "device_id": self.device_id,
                        "serial_port": self.serial_port,
                    },
                )
                self._client = ModbusSerialClient(
                    method="rtu",
                    port=self.serial_port,
                    baudrate=self._dev_obj.baudrate,
                    bytesize=self._dev_obj.bytesize,
                    parity=self._dev_obj.parity,
                    stopbits=self._dev_obj.stopbits,
                    timeout=self.timeout,
                )
                self._serial_clients.update({self.serial_port: self._client})
                self._serial_polling.update({self.serial_port: asyncio.Event()})
                self._serial_connected.update({self.serial_port: self._client.connect()})
            else:
                self._LOG.debug(
                    "Serial port already using. Getting client",
                    extra={
                        "device_id": self.device_id,
                        "serial_port": self.serial_port,
                    },
                )
                self._client = self._serial_clients[self.serial_port]
        else:
            raise NotImplementedError("Other Modbus variants not supported yet")

    def close_client(self) -> None:
        self._client.close()
        # if self.protocol is Protocol.MODBUS_RTU:
        #     self.__class__._serial_clients.pop(self.serial_port)
        #     self.__class__._serial_port_locks.pop(self.serial_port)

    # @property
    # def is_client_connected(self) -> bool:
    #     return self._connected

    @property
    def read_funcs(self) -> dict[ModbusReadFunc, Callable]:
        return {
            ModbusReadFunc.READ_COILS: self._client.read_coils,
            ModbusReadFunc.READ_DISCRETE_INPUTS: self._client.read_discrete_inputs,
            ModbusReadFunc.READ_HOLDING_REGISTERS: self._client.read_holding_registers,
            ModbusReadFunc.READ_INPUT_REGISTERS: self._client.read_input_registers,
        }

    @property
    def write_funcs(self) -> dict[ModbusWriteFunc, Callable]:
        return {
            ModbusWriteFunc.WRITE_COIL: self._client.write_coil,
            ModbusWriteFunc.WRITE_REGISTER: self._client.write_register,
            ModbusWriteFunc.WRITE_COILS: self._client.write_coils,
            ModbusWriteFunc.WRITE_REGISTERS: self._client.write_registers,
        }

    async def read(
        self, obj: BACnetObj, wait: bool = False, **kwargs: Any
    ) -> Optional[Union[int, float]]:
        if wait:
            await self._polling_event.wait()
        return await self._gtw.async_add_job(self.sync_read, obj)

    @log_exceptions
    def sync_read(self, obj: ModbusObj) -> Union[float, str]:
        """Read data from Modbus object.

        Updates object and return value.
        """
        if obj.func_read is ModbusReadFunc.READ_FILE:
            raise ModbusException("func-not-support")  # todo: implement 0x14 func
        resp = self.read_funcs[obj.func_read](
            address=obj.address, count=obj.quantity, unit=self.unit
        )
        if resp.isError():
            raise ModbusIOException(str(resp))

        value = self._decode_response(resp=resp, obj=obj)

        obj.set_property_value(value=value)
        return value  # fixme return not used now. Updates object

    async def write(
        self, value: Union[int, float], obj: BACnetObj, wait: bool = False, **kwargs: Any
    ) -> None:
        await self._gtw.async_add_job(self.sync_write, value, obj)

    @log_exceptions
    def sync_write(self, value: Union[int, float], obj: ModbusObj) -> None:
        """Write value to Modbus object.

        Args:
            value: Value to write
            obj: Object instance.
        """
        if obj.func_write is None:
            raise ModbusException("Object cannot be overwritten")

        payload = self._build_payload(value=value, obj=obj)

        if obj.func_write is ModbusWriteFunc.WRITE_REGISTER and isinstance(payload, list):
            # FIXME: hotfix
            assert len(payload) == 1
            payload = payload[0]  # type: ignore

        request = self.write_funcs[obj.func_write](obj.address, payload, unit=self.unit)
        if request.isError():
            raise ModbusIOException("0x80")  # todo: resp.string
        self._LOG.debug(
            "Successfully write",
            extra={
                "device_id": self.device_id,
                "object_id": obj.id,
                "object_type": obj.type,
                "address": obj.address,
                "value": value,
            },
        )
        # except (ModbusException, struct.error, Exception) as e:
        #     self._LOG.warning(
        #         "Failed write",
        #         extra={
        #             "device_id": self.id,
        #             "object_id": obj.id,
        #             "object_type": obj.type,
        #             "register": obj.address,
        #             "quantity": obj.quantity,
        #             "exc": e,
        #         },
        #     )
        # except Exception as e:
        #     self._LOG.exception('Unhandled error',
        #                         extra={'device_id': self.id, 'object_id': obj.id,
        #                                'object_type': obj.type, 'register': obj.address,
        #                                'quantity': obj.quantity, 'exc': e, })

    async def _poll_objects(self, objs: Collection[BACnetObj]) -> None:
        # def _sync_poll_objects(objs_: Collection[BACnetObj]) -> None:
        #     for obj in objs_:
        #         self.sync_read(obj=obj)
        #
        # await self._gateway.async_add_job(_sync_poll_objects, objs)
        for obj in objs:
            await self.read(obj=obj)

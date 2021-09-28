from typing import Any, Callable, Optional, Union

from pymodbus.client.sync import ModbusSerialClient, ModbusTcpClient  # type: ignore
from pymodbus.exceptions import ModbusException, ModbusIOException  # type: ignore
from pymodbus.framer.rtu_framer import ModbusRtuFramer  # type: ignore
from pymodbus.framer.socket_framer import ModbusSocketFramer  # type: ignore

from ..schemas import (
    BACnetObj,
    DeviceObj,
    ModbusObj,
    ModbusReadFunc,
    ModbusWriteFunc,
    Protocol,
    SerialDevicePropertyList,
    TcpIpModbusDevicePropertyList,
)
from ..utils import log_exceptions
from ._modbus_coder_mixin import ModbusCoderMixin
from .base_polling_device import BasePollingDevice


class ModbusDevice(BasePollingDevice, ModbusCoderMixin):
    """Sync Modbus Device.

    Note: AsyncModbusDevice in `pymodbus` didn't work correctly. So support only Sync
        client.
    """

    @staticmethod
    def interface_name(device_obj: DeviceObj) -> str:
        if isinstance(device_obj.property_list, TcpIpModbusDevicePropertyList):
            return device_obj.property_list.address_port
        if isinstance(device_obj.property_list, SerialDevicePropertyList):
            return device_obj.property_list.rtu.port
        raise NotImplementedError

    @log_exceptions
    async def create_client(
        self, device_obj: DeviceObj
    ) -> Union[ModbusTcpClient, ModbusSerialClient]:
        """Initializes synchronous modbus client."""

        self._LOG.debug(
            "Creating pymodbus client", extra={"device_id": device_obj.device_id}
        )
        framer = (
            ModbusRtuFramer
            if device_obj.property_list.protocol is Protocol.MODBUS_RTU
            else ModbusSocketFramer
        )

        if device_obj.property_list.protocol in {
            Protocol.MODBUS_TCP,
            Protocol.MODBUS_RTU_OVER_TCP,
        }:
            client = ModbusTcpClient(
                host=str(device_obj.property_list.address),  # type: ignore
                port=device_obj.property_list.port,  # type: ignore
                framer=framer,
                retries=device_obj.property_list.retries,
                retry_on_empty=True,
                retry_on_invalid=True,
                timeout=device_obj.property_list.timeout_seconds,
            )
            return client
        if device_obj.property_list.protocol is Protocol.MODBUS_RTU:
            client = ModbusSerialClient(
                method="rtu",
                port=device_obj.property_list.rtu.port,  # type: ignore
                baudrate=device_obj.property_list.rtu.baudrate,  # type: ignore
                bytesize=device_obj.property_list.rtu.bytesize,  # type: ignore
                parity=device_obj.property_list.rtu.parity,  # type: ignore
                stopbits=device_obj.property_list.rtu.stopbits,  # type: ignore
                timeout=device_obj.property_list.timeout_seconds,
            )
            return client
        raise NotImplementedError("Other Modbus variants not supported yet")

    @property
    def is_client_connected(self) -> bool:
        return self.interface.client_connected

    async def connect_client(
        self, client: Union[ModbusTcpClient, ModbusSerialClient]
    ) -> bool:
        return client.connect()

    async def _disconnect_client(
        self, client: Union[ModbusTcpClient, ModbusSerialClient]
    ) -> None:
        client.close()

    @property
    def read_funcs(self) -> dict[ModbusReadFunc, Callable]:
        client = self.interface.client
        return {
            ModbusReadFunc.READ_COILS: client.read_coils,
            ModbusReadFunc.READ_DISCRETE_INPUTS: client.read_discrete_inputs,
            ModbusReadFunc.READ_HOLDING_REGISTERS: client.read_holding_registers,
            ModbusReadFunc.READ_INPUT_REGISTERS: client.read_input_registers,
        }

    @property
    def write_funcs(self) -> dict[ModbusWriteFunc, Callable]:
        client = self.interface.client
        return {
            ModbusWriteFunc.WRITE_COIL: client.write_coil,
            ModbusWriteFunc.WRITE_REGISTER: client.write_register,
            ModbusWriteFunc.WRITE_COILS: client.write_coils,
            ModbusWriteFunc.WRITE_REGISTERS: client.write_registers,
        }

    async def read(
        self, obj: BACnetObj, wait: bool = False, **kwargs: Any
    ) -> Optional[Union[int, float]]:
        if wait:
            await self.interface.polling_event.wait()
        return await self._gtw.async_add_job(self.sync_read, obj)

    @log_exceptions
    def sync_read(self, obj: ModbusObj) -> ModbusObj:
        """Read data from Modbus object.

        Updates object and return value.
        """
        resp = self.read_funcs[obj.func_read](
            address=obj.address,
            count=obj.quantity,
            unit=self._device_obj.property_list.rtu.unit,  # type: ignore
        )
        if resp.isError():
            obj.set_property(value=ModbusIOException(str(resp)))
        else:
            value = self._decode_response(resp=resp, obj=obj)
            obj.set_property(value=value)
        return obj

    async def write(
        self, value: Union[int, float], obj: BACnetObj, wait: bool = False, **kwargs: Any
    ) -> None:
        await self._gtw.async_add_job(self.sync_write, value, obj)

    # @log_exceptions
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

        request = self.write_funcs[obj.func_write](
            obj.address,
            payload,
            unit=self._device_obj.property_list.rtu.unit,  # type: ignore
        )
        if request.isError():
            raise ModbusIOException("0x80")  # todo: resp.string
        self._LOG.debug(
            "Successfully write",
            extra={
                "device_id": self.id,
                "object_id": obj.id,
                "object_type": obj.type,
                "address": obj.address,
                "value": value,
            },
        )

    # async def _poll_objects(self, objs: Collection[BACnetObj]) -> None:
    #
    #     for obj in objs:
    #         if obj.existing:
    #             await self.read(obj=obj)

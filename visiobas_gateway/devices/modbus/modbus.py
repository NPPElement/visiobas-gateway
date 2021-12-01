from __future__ import annotations

from ipaddress import IPv4Address
from typing import Any, Callable

from pymodbus.client.sync import ModbusSerialClient, ModbusTcpClient  # type: ignore
from pymodbus.exceptions import ModbusException, ModbusIOException  # type: ignore
from pymodbus.framer.rtu_framer import ModbusRtuFramer  # type: ignore
from pymodbus.framer.socket_framer import ModbusSocketFramer  # type: ignore

from ...schemas import (
    BACnetObj,
    DeviceObj,
    ModbusObj,
    ModbusReadFunc,
    ModbusSerialDeviceObj,
    ModbusTCPDeviceObj,
    ModbusWriteFunc,
    Protocol,
    SerialPort,
)
from ...utils import get_file_logger, log_exceptions, ping, serial_port_connected
from .._interface import InterfaceKey
from ..base_polling_device import BasePollingDevice
from ._modbus_coder_mixin import ModbusCoderMixin

_LOG = get_file_logger(name=__name__)


class ModbusDevice(BasePollingDevice, ModbusCoderMixin):
    """Sync Modbus Device.

    Note: AsyncModbusDevice in `pymodbus` didn't work correctly. So support only Sync
        client.
    """

    @staticmethod
    def interface_key(device_obj: DeviceObj) -> InterfaceKey:
        return device_obj.property_list.interface

    @staticmethod
    async def is_reachable(device_obj: DeviceObj) -> bool:
        interface_key = device_obj.property_list.interface
        if isinstance(interface_key, SerialPort):
            return serial_port_connected(serial_port=interface_key)
        if isinstance(interface_key, tuple) and isinstance(interface_key[0], IPv4Address):
            return await ping(host=str(interface_key[0]), attempts=4)
        raise ValueError

    @log_exceptions(logger=_LOG)
    async def create_client(
        self, device_obj: ModbusSerialDeviceObj | ModbusTCPDeviceObj
    ) -> ModbusTcpClient | ModbusSerialClient:
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
                host=str(device_obj.property_list.ip),  # type: ignore
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

    async def connect_client(self, client: ModbusTcpClient | ModbusSerialClient) -> bool:
        return client.connect()

    async def _disconnect_client(
        self, client: ModbusTcpClient | ModbusSerialClient
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

    async def read(self, obj: BACnetObj, wait: bool = False, **kwargs: Any) -> BACnetObj:
        if not isinstance(obj, ModbusObj):
            raise ValueError(f"`obj` must be `ModbusObj`. Got {type(obj)}")
        if wait:
            await self.interface.polling_event.wait()
        return await self._gtw.async_add_job(self.sync_read, obj)

    @log_exceptions(logger=_LOG)
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
        self, value: int | float | str, obj: BACnetObj, wait: bool = False, **kwargs: Any
    ) -> None:
        if not isinstance(obj, ModbusObj):
            raise ValueError(f"`obj` must be `ModbusObj`. Got {type(obj)}")
        await self._gtw.async_add_job(self.sync_write, value, obj)

    def sync_write(self, value: int | float | str, obj: ModbusObj) -> None:
        """Write value to Modbus object.

        Args:
            value: Value to write
            obj: Object instance.
        """
        if obj.func_write is None:
            raise ModbusException("Object cannot be overwritten")
        if isinstance(value, str):
            raise NotImplementedError("Modbus expected numbers to write. Got `str`.")

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
        self._LOG.debug("Successfully write", extra={"object": obj, "value": value})

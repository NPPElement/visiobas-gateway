from abc import abstractmethod
from typing import TYPE_CHECKING, Callable, Optional, Union

from pymodbus.bit_read_message import (  # type: ignore
    ReadBitsResponseBase,
    ReadCoilsResponse,
    ReadDiscreteInputsResponse,
)
from pymodbus.client.asynchronous.async_io import (  # type: ignore
    AsyncioModbusSerialClient,
    AsyncioModbusTcpClient,
)
from pymodbus.client.sync import ModbusSerialClient, ModbusTcpClient  # type: ignore
from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder  # type: ignore
from pymodbus.register_read_message import (  # type: ignore
    ReadHoldingRegistersResponse,
    ReadInputRegistersResponse,
    ReadRegistersResponseBase,
)

from ..schemas import DeviceObj, ModbusDataType, ModbusObj, ModbusReadFunc, ModbusWriteFunc
from .base_polling_device import BasePollingDevice

if TYPE_CHECKING:
    from ..gateway import Gateway
else:
    Gateway = "Gateway"


# _LOG = get_file_logger(name=__name__, size_mb=500)


class BaseModbusDevice(BasePollingDevice):
    """Base class for Modbus devices.
    Note: Used when sync\async devices supported.
    """

    def __init__(self, device_obj: DeviceObj, gateway: Gateway) -> None:
        super().__init__(device_obj, gateway)

        self._client: Optional[
            Union[
                ModbusSerialClient,
                ModbusTcpClient,
                AsyncioModbusTcpClient,
                AsyncioModbusSerialClient,
            ]
        ] = None

    @property
    def unit(self) -> int:
        if hasattr(self._dev_obj.property_list, "rtu"):
            return self._dev_obj.property_list.rtu.unit  # type: ignore
        return 0x01

    @property
    @abstractmethod
    def read_funcs(self) -> dict[ModbusReadFunc, Callable]:
        raise NotImplementedError

    @property
    @abstractmethod
    def write_funcs(self) -> dict[ModbusWriteFunc, Callable]:
        raise NotImplementedError

    def _decode_response(
        self,
        resp: Union[
            ReadCoilsResponse,
            ReadDiscreteInputsResponse,
            ReadHoldingRegistersResponse,
            ReadInputRegistersResponse,
        ],
        obj: ModbusObj,
    ) -> Union[bool, int, float]:
        """Decodes value from registers and scale them.
        # TODO make 4 decoders for all combinations in bo, wo and use them?
        Args:
            resp: Read request response.
            obj: Object instance

        Returns:
            Decoded from register\bits and scaled value.
        """

        # TODO: Add decode with different byteorder in bytes VisioDecoder class

        if isinstance(resp, ReadBitsResponseBase):
            data = resp.bits
            return 1 if data[0] else 0  # TODO: add support several bits?
        if isinstance(resp, ReadRegistersResponseBase):
            data = resp.registers
            scaled: Union[float, int]
            if obj.data_type == ModbusDataType.BOOL:
                if obj.data_length == 1:
                    scaled = decoded = 1 if data[0] else 0
                elif obj.bit:
                    scaled = decoded = 1 if data[obj.bit] else 0
                else:
                    scaled = decoded = any(data)
            else:
                decoder = BinaryPayloadDecoder.fromRegisters(
                    registers=data, byteorder=obj.byte_order, wordorder=obj.word_order
                )
                decode_funcs = {
                    ModbusDataType.BITS: decoder.decode_bits,
                    # DataType.BOOL: None,
                    # DataType.STR: decoder.decode_string,
                    8: {
                        ModbusDataType.INT: decoder.decode_8bit_int,
                        ModbusDataType.UINT: decoder.decode_8bit_uint,
                    },
                    16: {
                        ModbusDataType.INT: decoder.decode_16bit_int,
                        ModbusDataType.UINT: decoder.decode_16bit_uint,
                        ModbusDataType.FLOAT: decoder.decode_16bit_float,
                        # DataType.BOOL: None,
                    },
                    32: {
                        ModbusDataType.INT: decoder.decode_32bit_int,
                        ModbusDataType.UINT: decoder.decode_32bit_uint,
                        ModbusDataType.FLOAT: decoder.decode_32bit_float,
                    },
                    64: {
                        ModbusDataType.INT: decoder.decode_64bit_int,
                        ModbusDataType.UINT: decoder.decode_64bit_uint,
                        ModbusDataType.FLOAT: decoder.decode_64bit_float,
                    },
                }
                assert decode_funcs[obj.data_length][obj.data_type] is not None

                decoded = decode_funcs[obj.data_length][obj.data_type]()
                scaled = decoded * obj.scale + obj.offset  # Scaling
            self._LOG.debug(
                "Decoded",
                extra={
                    "device_id": obj.device_id,
                    "object_id": obj.id,
                    "object_type": obj.type,
                    "address": obj.address,
                    "object_is_register": obj.is_register,
                    "objects_is_coil": obj.is_coil,
                    "word_order": obj.word_order,
                    "byte_order": obj.byte_order,
                    "quantity": obj.quantity,
                    "data_length": obj.data_length,
                    "data_type": obj.data_type,
                    "value_raw": data,
                    "value_decoded": decoded,
                    "value_scaled": scaled,
                },
            )
            return scaled
        raise NotImplementedError

    def _build_payload(
        self, value: Union[int, float], obj: ModbusObj
    ) -> Union[int, list[Union[int, bytes, bool]]]:
        """
        # TODO make 4 decoders for all combinations in bo, wo and use them?
        Args:
            value: Value to write in object.
            obj: Object instance.

        Returns:
            Built payload.
        """
        scaled = int(value / obj.scale - obj.offset)  # Scaling

        # In `pymodbus` example INT and UINT values presented by hex values.
        # value = hex(value) if obj.data_type in {DataType.INT, DataType.UINT} else value

        if obj.data_type is ModbusDataType.BOOL and obj.data_length in {1, 16}:
            # scaled = [scaled] + [0] * 7
            return int(bool(scaled))

        builder = BinaryPayloadBuilder(byteorder=obj.byte_order, wordorder=obj.word_order)
        build_funcs = {
            # 1: {DataType.BOOL: builder.add_bits},
            8: {
                ModbusDataType.INT: builder.add_8bit_int,
                ModbusDataType.UINT: builder.add_8bit_uint,
                # DataType.BOOL: builder.add_bits,
            },
            16: {
                ModbusDataType.INT: builder.add_16bit_int,
                ModbusDataType.UINT: builder.add_16bit_uint,
                ModbusDataType.FLOAT: builder.add_16bit_float,
                # DataType.BOOL: builder.add_bits,
            },
            32: {
                ModbusDataType.INT: builder.add_32bit_int,
                ModbusDataType.UINT: builder.add_32bit_uint,
                ModbusDataType.FLOAT: builder.add_32bit_float,
            },
            64: {
                ModbusDataType.INT: builder.add_64bit_int,
                ModbusDataType.UINT: builder.add_64bit_uint,
                ModbusDataType.FLOAT: builder.add_64bit_float,
            },
        }
        assert build_funcs[obj.data_length][obj.data_type] is not None

        build_funcs[obj.data_length][obj.data_type](scaled)

        # FIXME: string not support now
        payload = builder.to_coils() if obj.is_coil else builder.to_registers()

        # payload = builder.build()
        self._LOG.debug(
            "Encoded",
            extra={
                "device_id": obj.device_id,
                "object_id": obj.id,
                "object_type": obj.type,
                "object_is_register": obj.is_register,
                "objects_is_coil": obj.is_coil,
                "address": obj.address,
                "word_order": obj.word_order,
                "byre_order": obj.byte_order,
                "quantity": obj.quantity,
                "data_length": obj.data_length,
                "data_type": obj.data_type,
                "value_raw": value,
                "value_scaled": scaled,
                "value_encoded": payload,
            },
        )
        return payload

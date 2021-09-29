from typing import Union

from pymodbus.bit_read_message import (  # type: ignore
    ReadBitsResponseBase,
    ReadCoilsResponse,
    ReadDiscreteInputsResponse,
)
from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder  # type: ignore
from pymodbus.register_read_message import (  # type: ignore
    ReadHoldingRegistersResponse,
    ReadInputRegistersResponse,
    ReadRegistersResponseBase,
)

from ..schemas import ModbusDataType, ModbusObj
from ..utils import get_file_logger

_LOG = get_file_logger(name=__name__)


class ModbusCoderMixin:
    """Mixin for encode/decode interact with `pymodbus`."""

    @staticmethod
    def _decode_response(
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
                if obj.bit and obj.data_length == 1:
                    value = format(data[0], '0>16b')
                    value = list(reversed(value))[obj.bit]
                    scaled = decoded = int(value)
                elif obj.data_length == 1:
                    scaled = decoded = 1 if data[0] else 0
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
            _LOG.debug(
                "Decoded",
                extra={
                    "object": obj,
                    "value_raw": data,
                    "value_decoded": decoded,
                    "value_scaled": scaled,
                },
            )
            return scaled
        raise NotImplementedError

    @staticmethod
    def _build_payload(
        value: Union[int, float], obj: ModbusObj
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

        _LOG.debug(
            "Encoded",
            extra={
                "object": obj,
                "value_raw": value,
                "value_scaled": scaled,
                "value_encoded": payload,
            },
        )
        return payload

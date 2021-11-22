from __future__ import annotations

from typing import Any, Sequence

from pymodbus.bit_read_message import ReadBitsResponseBase  # type: ignore

# ReadCoilsResponse, ReadDiscreteInputsResponse,
from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder  # type: ignore
from pymodbus.register_read_message import ReadRegistersResponseBase  # type: ignore

from ...schemas import READ_BITS_FUNCS, READ_REGISTER_FUNCS, ModbusDataType, ModbusObj
from ...utils import get_file_logger

# ReadHoldingRegistersResponse, ReadInputRegistersResponse,


_LOG = get_file_logger(name=__name__)

_BaseResponse: Any  # ReadBitsResponseBase | ReadRegistersResponseBase
_ImplementedResponse: Any  # (
#     ReadCoilsResponse
#     | ReadDiscreteInputsResponse
#     | ReadHoldingRegistersResponse
#     | ReadInputRegistersResponse
# )
_DecodedValue: Any  # bool | int | float


class ModbusCoderMixin:
    """Mixin for encode/decode interact with `pymodbus`."""

    @staticmethod
    def _extract_data(response: _ImplementedResponse) -> list:
        if isinstance(response, ReadBitsResponseBase):
            return response.bits
        if isinstance(response, ReadRegistersResponseBase):
            return response.registers
        raise ValueError(
            f"Expected response `{_ImplementedResponse}` Got `{type(response)}`"
        )

    @staticmethod
    def _decode_bool(data: list, obj: ModbusObj) -> int | bool:
        if obj.bit and obj.data_length == 1:
            value = format(data[0], "0>16b")
            return int(list(reversed(value))[obj.bit])
        if obj.data_length == 1:
            return 1 if data[0] else 0
        return any(data)

    @staticmethod
    def _decode_response(
        response: _ImplementedResponse, objs: ModbusObj | Sequence[ModbusObj]
    ) -> _DecodedValue | list[_DecodedValue]:
        data = ModbusCoderMixin._extract_data(response=response)
        if isinstance(objs, Sequence) and len(objs) == 1:
            objs = objs[0]
        if isinstance(objs, ModbusObj):
            return ModbusCoderMixin._decode_single_data(data=data, obj=objs)
        if isinstance(objs, Sequence):
            return ModbusCoderMixin._decode_multiple_data(data=data, objs=objs)
        raise NotImplementedError

    @staticmethod
    def _decode_single_data(
        data: list,
        obj: ModbusObj,
    ) -> _DecodedValue:
        """Decodes value from registers and scale them.

        Args:
            data:
            obj: Object instance

        Returns:
            Decoded and scaled value.

        # TODO make 4 decoders for all combinations in bo, wo and use them?
        # TODO: Add decode with different byteorder in bytes VisioDecoder class
        """
        if not data:
            raise ValueError(f"Expected non-empty `data`. Got `{data}`")

        if obj.func_read in READ_BITS_FUNCS:
            # TODO: add support several bits?
            return 1 if data[0] else 0
        if obj.func_read not in READ_REGISTER_FUNCS:
            raise NotImplementedError
        if obj.data_type == ModbusDataType.BOOL:
            return ModbusCoderMixin._decode_bool(data=data, obj=obj)

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
        if (
            decode_funcs.get(obj.data_length) is None
            or decode_funcs[obj.data_length].get(obj.data_type) is None
        ):
            raise NotImplementedError

        decoded = decode_funcs[obj.data_length][obj.data_type]()
        scaled = decoded * obj.scale + obj.offset
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

    @staticmethod
    def _decode_multiple_data(data: list, objs: Sequence[ModbusObj]) -> list[_DecodedValue]:
        register_counter = 0
        values: list[_DecodedValue] = []

        for obj in objs:
            obj_data = data[register_counter : obj.quantity]  # noqa
            value = ModbusCoderMixin._decode_single_data(data=obj_data, obj=obj)
            values.append(value)
            register_counter += obj.quantity
        if len(values) != len(objs):
            raise ValueError(
                "Decode error! Lengths of decoded values and objects not equals."
            )
        return values

    @staticmethod
    def _build_payload(
        value: int | float, obj: ModbusObj
    ) -> int | list[int | bytes | bool]:
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
        if (
            build_funcs.get(obj.data_length) is None
            or build_funcs[obj.data_length].get(obj.data_type) is None
        ):
            raise NotImplementedError

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

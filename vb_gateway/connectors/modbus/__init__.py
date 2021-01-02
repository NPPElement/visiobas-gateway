from typing import NamedTuple

from pymodbus.payload import BinaryPayloadDecoder

from vb_gateway.connectors.bacnet import ObjType


class VisioModbusProperties(NamedTuple):
    scale: int
    data_type: str
    data_length: int
    byte_order: str

    bit: int or None = None


class ModbusObject(NamedTuple):
    type: ObjType
    id: int
    name: str

    address: int
    quantity: int
    func_read: int

    properties: VisioModbusProperties


def cast_to_bit(register: list[int], bit: int) -> int:
    """ Extract a bit from 1 register"""
    # TODO: implement several bits

    if 0 >= bit >= 15:
        raise ValueError("Parameter 'bit' must be 0 <= bit <= 15")

    decoder = BinaryPayloadDecoder.fromRegisters(registers=register)
    first = decoder.decode_bits()
    second = decoder.decode_bits()
    bits = [*second, *first]
    return int(bits[bit])


def cast_2_registers(registers: list[int],
                     byteorder: str,
                     wordorder: str,
                     type_name: str) -> int or float:
    """ Cast two registers to selected type"""
    decoder = BinaryPayloadDecoder.fromRegisters(
        registers=registers,
        byteorder=byteorder,
        wordorder=wordorder
    )
    if type_name == 'FLOAT':
        return decoder.decode_32bit_float()
    elif type_name == 'INT':
        return decoder.decode_32bit_int()
    elif type_name == 'UINT':
        return decoder.decode_32bit_uint()
    else:
        raise NotImplementedError('That type not implemented yet')

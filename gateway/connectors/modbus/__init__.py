from typing import NamedTuple

from pymodbus.payload import BinaryPayloadDecoder

from gateway.connectors.bacnet import BACnetObject


class VisioModbusProperties(NamedTuple):
    scale: int  # TODO: change to 'multiplier' \ change operation in scaled value

    # for recalculate (A*X+B)
    multiplier: float  # A
    corrective: float  # B

    data_type: str
    data_length: int  # the number of bits in which the value is stored

    byte_order: str
    word_order: str

    bitmask = int
    bit: int or None = None  # TODO: change to 'bitmask'


class ModbusObject(BACnetObject):
    address: int
    quantity: int
    func_read: int

    properties: VisioModbusProperties


def cast_to_bit(register: list[int], bit: int) -> int:
    """ Extract a bit from 1 register """
    # TODO: implement several bits

    if 0 >= bit >= 15:
        raise ValueError("Parameter 'bit' must be 0 <= bit <= 15")

    decoder = BinaryPayloadDecoder.fromRegisters(registers=register)
    first = decoder.decode_bits()
    second = decoder.decode_bits()
    bits = [*second, *first]
    return int(bits[bit])


def cast_2_registers(registers: list[int],
                     byteorder: str, wordorder: str,
                     type_name: str) -> int or float:
    """ Cast two registers to selected type"""
    decoder = BinaryPayloadDecoder.fromRegisters(
        registers=registers,
        byteorder=byteorder,
        wordorder=wordorder
    )
    decode_func = {16: {'INT': decoder.decode_16bit_int,
                        'UINT': decoder.decode_16bit_uint,
                        'FLOAT': decoder.decode_16bit_float,
                        },
                   32: {'INT': decoder.decode_32bit_int,
                        'UINT': decoder.decode_32bit_uint,
                        'FLOAT': decoder.decode_32bit_float,
                        },
                   }
    # TODO: UNFINISHED
    raise NotImplementedError
    try:
        return decode_func[type_name]()
    except KeyError:
        raise ValueError(f'Behavior for <{type_name}> not implemented')

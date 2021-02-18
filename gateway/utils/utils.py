from pymodbus.payload import BinaryPayloadDecoder

# FIXME
from gateway.models import ObjProperty


def get_fault_obj_properties(reliability: int or str,
                             pv='null',
                             sf: list = None) -> dict:
    """ Returns properties for unknown objects
    """
    if sf is None:
        sf = [0, 1, 0, 0]
    return {
        ObjProperty.presentValue: pv,
        ObjProperty.statusFlags: sf,
        ObjProperty.reliability: reliability
        #  todo: make reliability class as Enum
    }


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

# def cast_2_registers(registers: list[int],
#                      byteorder: str, wordorder: str,
#                      type_name: str) -> int or float:
#     """ Cast two registers to selected type"""
#     decoder = BinaryPayloadDecoder.fromRegisters(
#         registers=registers,
#         byteorder=byteorder,
#         wordorder=wordorder
#     )
#     decode_func = {16: {'INT': decoder.decode_16bit_int,
#                         'UINT': decoder.decode_16bit_uint,
#                         'FLOAT': decoder.decode_16bit_float,
#                         },
#                    32: {'INT': decoder.decode_32bit_int,
#                         'UINT': decoder.decode_32bit_uint,
#                         'FLOAT': decoder.decode_32bit_float,
#                         },
#                    }
#     # TODO: UNFINISHED
#     try:
#         return decode_func[type_name]()
#     except KeyError:
#         raise ValueError(f'Behavior for <{type_name}> not implemented')

from typing import NamedTuple

from pymodbus.payload import BinaryPayloadDecoder

from gateway.models.bacnet import ObjType, ObjProperty


class VisioModbusProperties(NamedTuple):
    address: int
    quantity: int
    func_read: int
    func_write: int

    scale: int  # TODO: change to 'multiplier' \ change operation in scaled value

    # for recalculate (A*X+B)
    # multiplier: float  # A # todo
    # corrective: float  # B# todo

    data_type: str
    data_length: int  # the number of bits in which the value is stored

    # byte_order: str # todo
    # word_order: str# todo

    # bitmask = int todo
    bit: int or None = None  # TODO: change to 'bitmask'

    @classmethod
    def create_from_json(cls, property_list: str):
        from json import loads

        modbus_properties = loads(property_list)['modbus']

        address = int(modbus_properties['address'])
        quantity = int(modbus_properties['quantity'])
        func_read = int(modbus_properties['functionRead'][-2:])
        func_write = int(modbus_properties.get('functionWrite', '0x06')[-2:])

        scale = int(modbus_properties.get('scale', 1))
        data_type = modbus_properties['dataType']
        data_length = modbus_properties.get('dataLength')
        bit = modbus_properties.get('bit')

        # byte_order = '<' if quantity == 1 else '>'
        # byte_order = None  # don't use now # todo

        # trying to fill the data if it is not enough FIXME
        if data_type == 'BOOL' and bit is None and data_length is None:
            data_length = 16
        elif data_type == 'BOOL' and isinstance(bit, int) and data_length is None:
            data_length = 1
        elif data_type != 'BOOL' and data_length is None and isinstance(quantity, int):
            data_length = quantity * 16

        return cls(address=address,
                   quantity=quantity,
                   func_read=func_read,
                   func_write=func_write,
                   scale=scale,
                   data_type=data_type,
                   data_length=data_length,
                   bit=bit
                   )


class ModbusObj(NamedTuple):
    type: ObjType
    id: int
    name: str
    # upd_period: int

    properties: VisioModbusProperties

    @classmethod
    def create_from_dict(cls, obj_type: ObjType, obj_props: dict):
        # FIXME: make convertation obj type from props (int)

        obj_id = obj_props[str(ObjProperty.objectIdentifier.id)]
        obj_name = obj_props[str(ObjProperty.objectName.id)]

        prop_list = obj_props[str(ObjProperty.propertyList.id)]

        vb_props = VisioModbusProperties.create_from_json(
            property_list=prop_list)

        return cls(type=obj_type,
                   id=obj_id,
                   name=obj_name,
                   properties=vb_props
                   )


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


if __name__ == '__main__':
    obj1 = ModbusObj(type=ObjType.BINARY_OUTPUT,
                     id=1,
                     name='',
                     properties=VisioModbusProperties(
                         address=1,
                         quantity=1,
                         func_read=3,
                         func_write=6,
                         scale=1,
                         data_type='INT',
                         data_length=16,
                         bit=None
                     ))

    obj2 = ModbusObj(type=ObjType.BINARY_OUTPUT,
                     id=1,
                     name='',
                     properties=VisioModbusProperties(
                         address=1,
                         quantity=1,
                         func_read=3,
                         func_write=6,
                         scale=1,
                         data_type='INT',
                         data_length=16,
                         bit=None
                     ))
    print(hash(obj1) == hash((ObjType.BINARY_OUTPUT, 1)))


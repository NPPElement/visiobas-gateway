from json import loads
from typing import NamedTuple

from pydantic import BaseModel, Field

from .func_code import ModbusFunc


class ModbusObjPropertyListModel(BaseModel):
    address: int = Field(gt=0)
    quantity: int = Field(gt=0)
    func_read: ModbusFunc = Field(..., alias='functionRead')
    func_write: ModbusFunc = Field(default=ModbusFunc.WRITE_REGISTER, alias='functionWrite')

    # for recalculate A*X+B
    scale: float = 1.0  # A
    offset: float = 0.0  # B

    data_type: str = Field(..., alias='dataType')  # todo Enum
    data_length: int = Field(default=16, gt=1, lt=64, alias='dataLength',
                             description='The number of bits in which the value is stored')

    byte_order: str = Field(default='little', alias='byteOrder')
    word_order: str = Field(default='big', alias='wordOrder')
    repack: bool = Field(default=False)  # todo add to docs

    # bitmask = int todo
    # bit: Union[int, None] = None  # TODO: change to 'bitmask'


class ModbusPropertyListWrapper(BaseModel):
    modbus: ModbusObjPropertyListModel = Field(...)  # alias='modbus')

    # @property
    # def address(self) -> int:
    #     return self.modbus.address
    #
    # @property
    # def func_read(self) -> ModbusFunc:
    #     return self.modbus.func_read
    #
    # @property
    # def func_write(self) -> ModbusFunc:
    #     return self.modbus.func_write
    #
    # @property
    # def quantity(self) -> int:
    #     return self.modbus.quantity

# class ModbusProperties(NamedTuple):
#     address: int
#     quantity: int
#     func_read: int
#     func_write: int
#
#     scale: int  # TODO: change to 'multiplier' \ change operation in scaled value
#
#     # for recalculate (A*X+B)
#     # multiplier: float  # A # todo
#     # corrective: float  # B# todo
#
#     data_type: str
#     data_length: int  # the number of bits in which the value is stored
#
#     # byte_order: str # todo
#     # word_order: str# todo
#
#     # bitmask = int todo
#     bit: int or None = None  # TODO: change to 'bitmask'
#
#     @classmethod
#     def create_from_json(cls, property_list: str):
#         modbus_properties = loads(property_list)['modbus']
#
#         address = int(modbus_properties['address'])
#         quantity = int(modbus_properties['quantity'])
#         func_read = int(modbus_properties['functionRead'][-2:])
#         func_write = int(modbus_properties.get('functionWrite', '0x06')[-2:])
#
#         scale = int(modbus_properties.get('scale', 1))
#         data_type = modbus_properties['dataType']
#         data_length = modbus_properties.get('dataLength')
#         bit = modbus_properties.get('bit')
#
#         # byte_order = '<' if quantity == 1 else '>'
#         # byte_order = None  # don't use now # todo
#
#         # trying to fill the data if it is not enough FIXME
#         if data_type == 'BOOL' and bit is None and data_length is None:
#             data_length = 16
#         elif data_type == 'BOOL' and isinstance(bit, int) and data_length is None:
#             data_length = 1
#         elif data_type != 'BOOL' and data_length is None and isinstance(quantity, int):
#             data_length = quantity * 16
#
#         return cls(address=address,
#                    quantity=quantity,
#                    func_read=func_read,
#                    func_write=func_write,
#                    scale=scale,
#                    data_type=data_type,
#                    data_length=data_length,
#                    bit=bit
#                    )

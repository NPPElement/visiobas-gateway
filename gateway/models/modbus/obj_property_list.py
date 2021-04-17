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

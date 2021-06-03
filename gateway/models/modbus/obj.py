from typing import Union, Optional

from pydantic import Field, Json, BaseModel, validator
from pymodbus.constants import Endian

from .data_type import DataType
from .func_code import ModbusReadFunc, ModbusWriteFunc
from ..bacnet.obj import BACnetObj, BACnetObjPropertyListModel
from ..bacnet.obj_property import ObjProperty


class ModbusObjPropertyListModel(BaseModel):
    address: int = Field(ge=0)
    quantity: int = Field(gt=0)
    func_read: ModbusReadFunc = Field(default=ModbusReadFunc.READ_HOLDING_REGISTERS,
                                      alias='functionRead')
    func_write: Optional[ModbusWriteFunc] = Field(
        default=None, alias='functionWrite',
        description='Function to write value. None if read only object.')

    # For recalculate A*X+B (X - value)
    scale: float = Field(default=1., description='Multiplier `A` for recalculate A*X+B')
    offset: float = Field(default=.0, description='Adding `B` for recalculate A*X+B')

    data_type: Union[DataType, str] = Field(..., alias='dataType')
    data_length: int = Field(default=16, ge=1, lt=64, alias='dataLength',
                             # todo calc default: quantity * 16
                             description='The number of bits in which the value is stored')

    byte_order: Union[str, Endian] = Field(default='little', alias='byteOrder')
    word_order: Union[str, Endian] = Field(default='big', alias='wordOrder')
    # repack: bool = Field(default=False)  # todo for encode

    # bitmask = int todo
    bit: Optional[int] = Field(default=None, ge=0, le=16)  # TODO: change to 'bitmask'?

    @validator('func_write')
    def validate_consistent(cls, v: ModbusWriteFunc, values) -> Optional[ModbusWriteFunc]:
        # TODO: add funcs mapping
        if v is None:
            return v
        elif values['func_read'].for_register and v.for_register:
            return v
        elif values['func_read'].for_coil and v.for_coil:
            return v
        else:
            raise ValueError('Make sure func_read and func_write are consistent.')

    class Config:
        arbitrary_types_allowed = True

    def __str__(self) -> str:
        return str(self.__dict__)

    def __repr__(self) -> str:
        return str(self)

    # @validator('bit')
    # def check_bit(cls, v, values):
    #     if 'data_length' in values and values['data_length'] > 1 and v is None:
    #         raise ValueError('If `data_length`==1, `bit` value expected')

    @validator('byte_order')
    def cast_byte_order(cls, v: str) -> Endian:
        return Endian.Big if v == 'big' else Endian.Little

    @validator('word_order')
    def cast_word_order(cls, v: str) -> Endian:
        return Endian.Big if v == 'big' else Endian.Little

    @validator('data_type')
    def cast_data_type(cls, v: Union[DataType, str]) -> DataType:
        if isinstance(v, str):
            return DataType(v.lower())
        return v


class ModbusPropertyListJsonModel(BACnetObjPropertyListModel):
    modbus: ModbusObjPropertyListModel = Field(...)

    def __str__(self) -> str:
        return str(self.__dict__)

    def __repr__(self) -> str:
        return str(self)


class ModbusObj(BACnetObj):
    property_list: Json[ModbusPropertyListJsonModel] = Field(
        alias=ObjProperty.propertyList.id_str)

    def __str__(self) -> str:
        return str(self.__dict__)

    def __repr__(self) -> str:
        return str(self)

    @property
    def data_length(self) -> int:
        return self.property_list.modbus.data_length

    @property
    def data_type(self) -> DataType:
        return self.property_list.modbus.data_type

    @property
    def address(self) -> int:
        return self.property_list.modbus.address

    @property
    def quantity(self) -> int:
        return self.property_list.modbus.quantity

    @property
    def scale(self) -> float:
        return self.property_list.modbus.scale

    @property
    def offset(self) -> float:
        return self.property_list.modbus.offset

    @property
    def byte_order(self) -> Endian:
        return self.property_list.modbus.byte_order

    @property
    def word_order(self) -> Endian:
        return self.property_list.modbus.word_order

    @property
    def bit(self) -> Optional[int]:
        return self.property_list.modbus.bit

    @property
    def is_register(self) -> bool:
        return self.func_read.for_register

    @property
    def is_coil(self) -> bool:
        return self.func_read.for_coil

    @property
    def func_read(self) -> ModbusReadFunc:
        return self.property_list.modbus.func_read

    @property
    def func_write(self) -> Optional[ModbusWriteFunc]:
        return self.property_list.modbus.func_write

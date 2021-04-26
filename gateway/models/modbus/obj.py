from pydantic import Field, Json, BaseModel

from .func_code import ModbusFunc
from ..bacnet.obj import BACnetObjModel, BACnetObjPropertyListModel
from ..bacnet.obj_property import ObjProperty


class ModbusObjPropertyListModel(BaseModel):
    address: int = Field(gt=0)
    quantity: int = Field(gt=0)
    func_read: ModbusFunc = Field(default=ModbusFunc.READ_HOLDING_REGISTERS,
                                  alias='functionRead')
    func_write: ModbusFunc = Field(default=ModbusFunc.WRITE_REGISTER, alias='functionWrite')

    # For recalculate A*X+B (X - value)
    scale: float = Field(default=1., description='Multiplier `A` for recalculate A*X+B')
    offset: float = Field(default=.0, description='Adding `B` for recalculate A*X+B')

    data_type: str = Field(..., alias='dataType')  # todo Enum
    data_length: int = Field(default=16, gt=1, lt=64, alias='dataLength',  # todo calc default: quantity *16
                             description='The number of bits in which the value is stored')

    byte_order: str = Field(default='little', alias='byteOrder')
    word_order: str = Field(default='big', alias='wordOrder')
    repack: bool = Field(default=False)  # todo add to docs

    # bitmask = int todo
    bit: int = Field(default=None)  # TODO: change to 'bitmask'

    def __repr__(self) -> str:
        return str(self.__dict__)


class ModbusPropertyListJsonModel(BACnetObjPropertyListModel):
    modbus: ModbusObjPropertyListModel = Field(...)

    def __repr__(self) -> str:
        return str(self.__dict__)


class ModbusObjModel(BACnetObjModel):
    property_list: Json[ModbusPropertyListJsonModel] = Field(
        alias=ObjProperty.propertyList.id_str)

    # @validator('property_list')
    # def parse_property_list(cls, pl: str) -> ModbusPropertyListWrap:
    #     return ModbusPropertyListWrap.parse_raw(pl)

    def __repr__(self) -> str:
        return f'ModbusObj'  # {self.__dict__}' # todo

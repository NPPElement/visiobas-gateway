from typing import Optional

from pydantic import Field

from ..bacnet.obj import BACnetObj
from ..bacnet.obj_property import ObjProperty
from .data_type import ModbusDataType
from .endian import Endian
from .func_code import READ_COIL_FUNCS, READ_REGISTER_FUNCS, ModbusReadFunc, ModbusWriteFunc
from .obj_property_list import ModbusPropertyList


class ModbusObj(BACnetObj):
    """Modbus Object."""

    property_list: ModbusPropertyList = Field(alias=str(ObjProperty.PROPERTY_LIST.value))

    @property
    def data_length(self) -> int:
        return self.property_list.modbus.data_length

    @property
    def data_type(self) -> ModbusDataType:
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
        return self.func_read in READ_REGISTER_FUNCS

    @property
    def is_coil(self) -> bool:
        return self.func_read in READ_COIL_FUNCS

    @property
    def func_read(self) -> ModbusReadFunc:
        return self.property_list.modbus.func_read

    @property
    def func_write(self) -> Optional[ModbusWriteFunc]:
        return self.property_list.modbus.func_write

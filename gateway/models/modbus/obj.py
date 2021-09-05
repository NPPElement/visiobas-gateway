from typing import Optional, Union

from pydantic import BaseModel, Field, validator

from ..bacnet.obj import BACnetObj
from ..bacnet.obj_property import ObjProperty
from ..bacnet.obj_property_list import BACnetObjPropertyListJsonModel
from .data_type import ModbusDataType
from .func_code import (
    READ_COIL_FUNCS,
    READ_REGISTER_FUNCS,
    WRITE_COIL_FUNCS,
    WRITE_REGISTER_FUNCS,
    ModbusReadFunc,
    ModbusWriteFunc,
)

try:
    from pymodbus.constants import Endian  # type: ignore
except ImportError as exc:
    raise NotImplementedError from exc


class ModbusObjPropertyListModel(BaseModel):
    """Represent Modbus PropertyList (371)."""

    address: int = Field(ge=0)
    quantity: int = Field(gt=0)
    func_read: ModbusReadFunc = Field(
        default=ModbusReadFunc.READ_HOLDING_REGISTERS, alias="functionRead"
    )
    func_write: Optional[ModbusWriteFunc] = Field(
        default=None,
        alias="functionWrite",
        description="Function to write value. None if read only object.",
    )

    # For recalculate A*X+B (X - value)
    scale: float = Field(default=1.0, description="Multiplier `A` for recalculate A*X+B")
    offset: float = Field(default=0.0, description="Adding `B` for recalculate A*X+B")

    data_type: ModbusDataType = Field(..., alias="dataType")
    data_length: int = Field(
        default=16,
        ge=1,
        lt=64,
        alias="dataLength",
        # todo calc default: quantity * 16
        description="The number of bits in which the value is stored",
    )

    byte_order: Union[str, Endian] = Field(default="little", alias="byteOrder")
    word_order: Union[str, Endian] = Field(default="big", alias="wordOrder")
    # repack: bool = Field(default=False)  # todo for encode

    # bitmask = int todo
    bit: Optional[int] = Field(default=None, ge=0, le=16)  # TODO: change to 'bitmask'?

    @validator("func_write")
    def validate_consistent(
        cls, value: ModbusWriteFunc, values: dict
    ) -> Optional[ModbusWriteFunc]:
        # pylint: disable=no-self-argument
        # TODO: add funcs mapping
        if value is None:
            return value
        if values["func_read"] in READ_REGISTER_FUNCS and value in WRITE_REGISTER_FUNCS:
            return value
        if values["func_read"] in READ_COIL_FUNCS and value in WRITE_COIL_FUNCS:
            return value
        raise ValueError("Make sure func_read and func_write are consistent.")

    class Config:  # pylint: disable=missing-class-docstring
        arbitrary_types_allowed = True

    # @validator('bit')
    # def check_bit(cls, v, values):
    #     if 'data_length' in values and values['data_length'] > 1 and v is None:
    #         raise ValueError('If `data_length`==1, `bit` value expected')

    @validator("byte_order")
    def cast_byte_order(cls, value: str) -> Endian:
        # pylint: disable=no-self-argument
        return Endian.Big if value == "big" else Endian.Little

    @validator("word_order")
    def cast_word_order(cls, value: str) -> Endian:
        # pylint: disable=no-self-argument
        return Endian.Big if value == "big" else Endian.Little

    @validator("data_type")
    def cast_data_type(cls, value: Union[ModbusDataType, str]) -> ModbusDataType:
        # pylint: disable=no-self-argument
        if isinstance(value, str):
            return ModbusDataType(value.lower())
        return value


class ModbusPropertyListJsonModel(BACnetObjPropertyListJsonModel):
    """Property list (371) for Modbus devices."""

    modbus: ModbusObjPropertyListModel = Field(...)


class ModbusObj(BACnetObj):
    """Modbus Object."""

    property_list: ModbusPropertyListJsonModel = Field(
        alias=str(ObjProperty.propertyList.prop_id)
    )

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

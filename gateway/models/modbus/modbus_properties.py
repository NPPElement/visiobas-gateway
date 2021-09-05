from typing import Optional

from pydantic import BaseModel, Field, validator

from .data_type import ModbusDataType
from .endian import Endian, validate_endian
from .func_code import (
    READ_COIL_FUNCS,
    READ_REGISTER_FUNCS,
    WRITE_COIL_FUNCS,
    WRITE_REGISTER_FUNCS,
    ModbusReadFunc,
    ModbusWriteFunc,
)


class ModbusProperties(BaseModel):
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
    byte_order: Endian = Field(default=Endian.LITTLE, alias="byteOrder")
    word_order: Endian = Field(default=Endian.BIG, alias="wordOrder")

    # bitmask = int todo
    bit: Optional[int] = Field(default=None, ge=0, le=16)  # TODO: change to 'bitmask'?

    class Config:  # pylint: disable=missing-class-docstring
        arbitrary_types_allowed = True

    @validator("func_write")
    def validate_func_consistent(
        cls, value: ModbusWriteFunc, values: dict
    ) -> Optional[ModbusWriteFunc]:
        # pylint: disable=no-self-argument
        if value is None:
            return value
        if values["func_read"] in READ_REGISTER_FUNCS and value in WRITE_REGISTER_FUNCS:
            return value
        if values["func_read"] in READ_COIL_FUNCS and value in WRITE_COIL_FUNCS:
            return value
        raise ValueError("Make sure func_read and func_write are consistent.")

    # Validators
    validate_byte_order = validator("byte_order", allow_reuse=True)(validate_endian)
    validate_word_order = validator("word_order", allow_reuse=True)(validate_endian)

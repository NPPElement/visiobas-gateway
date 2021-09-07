from enum import Enum, unique


@unique
class ModbusReadFunc(str, Enum):
    """Represent codes of Modbus available functions to read.

    Separate str value needed for parsing.
    """

    READ_COILS = "0x01"
    READ_DISCRETE_INPUTS = "0x02"
    READ_HOLDING_REGISTERS = "0x03"
    READ_INPUT_REGISTERS = "0x04"

    # READ_FILE = 0x14  # not implemented


READ_REGISTER_FUNCS = {
    ModbusReadFunc.READ_HOLDING_REGISTERS,
    ModbusReadFunc.READ_INPUT_REGISTERS,
}
READ_COIL_FUNCS = {
    ModbusReadFunc.READ_COILS,
    ModbusReadFunc.READ_DISCRETE_INPUTS,
}


@unique
class ModbusWriteFunc(str, Enum):
    """Represent codes of Modbus available functions to write.

    Separate str value needed for parsing.
    """

    WRITE_COIL = "0x05"
    WRITE_REGISTER = "0x06"
    WRITE_COILS = "0x15"
    WRITE_REGISTERS = "0x16"


WRITE_REGISTER_FUNCS = {
    ModbusWriteFunc.WRITE_REGISTER,
    ModbusWriteFunc.WRITE_REGISTERS,
}
WRITE_COIL_FUNCS = {
    ModbusWriteFunc.WRITE_COIL,
    ModbusWriteFunc.WRITE_COILS,
}

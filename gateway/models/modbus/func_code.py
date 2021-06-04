from enum import Enum, unique


@unique
class ModbusReadFunc(Enum):
    """Represent codes of Modbus available functions to read.

    Separate str value needed for parsing.
    """
    READ_COILS = 0x01, '0x01'
    READ_DISCRETE_INPUTS = 0x02, '0x02'
    READ_HOLDING_REGISTERS = 0x03, '0x03'
    READ_INPUT_REGISTERS = 0x04, '0x04'

    READ_FILE = 0x14, '0x14'  # not implemented to usage

    def __new__(cls, *values):
        obj = object.__new__(cls)
        for other_value in values:
            cls._value2member_map_[other_value] = obj
        obj._all_values = values
        return obj

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}.{self.name}'

    @property
    def code(self) -> int:
        return self.value[0]

    @property
    def code_str(self) -> str:
        return self.value[1]

    @property
    def for_register(self) -> bool:
        return True if self in {ModbusReadFunc.READ_HOLDING_REGISTERS,
                                ModbusReadFunc.READ_INPUT_REGISTERS, } else False

    @property
    def for_coil(self) -> bool:
        return True if self in {ModbusReadFunc.READ_COILS,
                                ModbusReadFunc.READ_DISCRETE_INPUTS, } else False


@unique
class ModbusWriteFunc(Enum):
    """Represent codes of Modbus available functions to write.

    Separate str value needed for parsing.
    """
    WRITE_COIL = 0x05, '0x05'
    WRITE_REGISTER = 0x06, '0x06'
    WRITE_COILS = 0x15, '0x15'
    WRITE_REGISTERS = 0x16, '0x16'

    def __new__(cls, *values):
        obj = object.__new__(cls)
        for other_value in values:
            cls._value2member_map_[other_value] = obj
        obj._all_values = values
        return obj

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}.{self.name}'

    @property
    def code(self) -> int:
        return self.value[0]

    @property
    def code_str(self) -> str:
        return self.value[1]

    @property
    def for_register(self) -> bool:
        return True if self in {ModbusWriteFunc.WRITE_REGISTER,
                                ModbusWriteFunc.WRITE_REGISTERS, } else False

    @property
    def for_coil(self) -> bool:
        return True if self in {ModbusWriteFunc.WRITE_COIL,
                                ModbusWriteFunc.WRITE_COILS, } else False

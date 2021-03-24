from enum import Enum, unique


@unique
class ModbusFunc(Enum):
    """Represent codes of Modbus available functions.

    Separate str value needed for parsing.
    """
    READ_COILS = 0x01, '0x01'
    READ_DISCRETE_INPUTS = 0x02, '0x02'
    READ_HOLDING_REGISTERS = 0x03, '0x03'
    READ_INPUT_REGISTERS = 0x04, '0x04'

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


MODBUS_READ_FUNCTIONS = {ModbusFunc.READ_COILS,
                         ModbusFunc.READ_DISCRETE_INPUTS,
                         ModbusFunc.READ_HOLDING_REGISTERS,
                         ModbusFunc.READ_INPUT_REGISTERS}

MODBUS_WRITE_FUNCTIONS = {ModbusFunc.WRITE_COIL,
                          ModbusFunc.WRITE_REGISTER,
                          ModbusFunc.WRITE_COILS,
                          ModbusFunc.WRITE_REGISTERS}

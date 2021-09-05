from enum import Enum, unique


@unique
class ModbusDataType(str, Enum):
    """Possible types for Modbus objects."""

    BITS = "bits"
    BOOL = "bool"
    # STR = 'str'  # not support yet
    INT = "int"
    UINT = "uint"
    FLOAT = "float"

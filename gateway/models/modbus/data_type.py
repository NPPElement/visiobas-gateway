from enum import Enum, unique


@unique
class ModbusDataType(Enum):
    """Possible types for Modbus objects."""

    BITS = "bits"
    BOOL = "bool"
    # STR = 'str'  # not support yet
    INT = "int"
    UINT = "uint"
    FLOAT = "float"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}"

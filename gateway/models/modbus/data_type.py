from enum import Enum, unique


@unique
class DataType(Enum):
    BITS = 'bits'
    BOOL = 'bool'
    STR = 'str'
    INT = 'int'
    UINT = 'uint'
    FLOAT = 'float'

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}.{self.name}'

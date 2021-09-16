from enum import Enum, unique


@unique
class StopBits(int, Enum):
    """The number of bits sent after each character in a
    message to indicate the end of the byte.
    """

    _1 = 1
    _2 = 2

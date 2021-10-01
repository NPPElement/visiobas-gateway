from enum import Enum, unique


@unique
class Bytesize(int, Enum):
    """The number of bits in a byte of serial data. This can be one of 5, 6, 7, or 8."""

    _5 = 5
    _6 = 6
    _7 = 7
    _8 = 8

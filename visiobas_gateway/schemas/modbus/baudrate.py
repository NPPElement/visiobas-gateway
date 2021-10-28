from enum import IntEnum, unique


@unique
class BaudRate(IntEnum):
    """Baudrate for The baud rate to use for the serial device."""

    _2400 = 2_400
    _4800 = 4_800
    _9600 = 9_600
    _19200 = 19_200
    _38400 = 38_400
    _57600 = 57_600
    _115200 = 115_200

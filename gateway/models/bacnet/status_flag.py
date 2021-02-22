from enum import Enum, unique


@unique
class StatusFlag(Enum):
    """StatusFlags represent by int.

    For enable flag FAULT use:
        sf = sf | StatusFlags.FAULT

    For disable flag IN_ALARM use:
        sf = sf & ~ StatusFlags.IN_ALARM
    """
    OUT_OF_SERVICE = 0b1000
    OVERRIDEN = 0b0100
    FAULT = 0b0010
    IN_ALARM = 0b0001

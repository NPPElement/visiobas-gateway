from enum import Enum, unique


@unique
class StatusFlag(Enum):
    """StatusFlags represent by int.

    How to use:
        For enable flag FAULT use:
            sf = sf | StatusFlags.FAULT.value

        For disable flag IN_ALARM use:
            sf = sf & ~StatusFlags.IN_ALARM.value

            TODO add check flag
    """
    OUT_OF_SERVICE = 0b1000
    OVERRIDEN = 0b0100
    FAULT = 0b0010
    IN_ALARM = 0b0001

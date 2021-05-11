from enum import Enum, unique


@unique
class StatusFlag(Enum):
    """StatusFlag represent by int.

    Usage:
        - For enable flag FAULT use:
            sf |= StatusFlag.FAULT.value

        - For disable flag IN_ALARM use:
            sf &= ~StatusFlag.IN_ALARM.value

        - For check flag OVERRIDEN use:
            flag_enabled = bool(sf & StatusFlag.OVERRIDEN.value)
    """
    # принимается ли значения сервером
    OUT_OF_SERVICE = 0b1000  # не слать на сервер

    OVERRIDEN = 0b0100  # не слать на сервер
    FAULT = 0b0010
    IN_ALARM = 0b0001  # не слать на сервер

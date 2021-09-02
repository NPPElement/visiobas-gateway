from copy import copy
from enum import Enum, unique

from pydantic import BaseModel, Field


@unique
class StatusFlag(int, Enum):
    """StatusFlag representation by int."""

    OUT_OF_SERVICE = 0b1000  # does server receive data?
    OVERRIDEN = 0b0100
    FAULT = 0b0010
    IN_ALARM = 0b0001


class StatusFlags(BaseModel):
    """Represent Combination of 4 `StatusFlag`."""

    flags: int = Field(default=0b0000, ge=0, le=15)

    # fixme: move to bacnet
    # @validator("flags")
    # def validate_flags(cls, value: Union[int, list[StatusFlag]]) -> int:
    #     # pylint: disable=no-self-argument
    #     if isinstance(value, int):
    #         return value
    #     if isinstance(value, (list, tuple)):
    #         sf_int = 0b0000
    #         for i, flag in enumerate(value):
    #             if flag == 1:
    #                 sf_int |= 1 << len(value) - 1 - i
    #             elif flag == 0:
    #                 continue
    #             raise ValueError('flags must be 0 | 1')
    #         return sf_int
    #     raise ValueError("Expected StatusFlags")

    def enable(self, flag: StatusFlag) -> "StatusFlags":
        """Enables flag.

        Args:
            flag: Status flag to enable.
        """
        if isinstance(flag, StatusFlag):
            self.flags |= flag.value
            return self
        raise ValueError("StatusFlag expected")

    def disable(self, flag: StatusFlag) -> "StatusFlags":
        """Disables flag.

        Args:
            flag: Status flag to disable.
        """
        if isinstance(flag, StatusFlag):
            self.flags &= ~flag.value
            return self
        raise ValueError("StatusFlag expected")

    def check(self, flag: StatusFlag) -> bool:
        """Checks the flag is enabled.

        Args:
            flag: Status flag to check.

        Returns:
            Is flag enabled.
        """
        return bool(self.flags & flag.value)

    @property
    def for_http(self) -> "StatusFlags":
        """
        Returns:
            Copy of StatusFlags, with except: disabled flags:
                - OUT_OF_SERVICE
                - OVERRIDEN
                - IN_ALARM
        """
        sf_copy = copy(self)
        sf_copy.disable(flag=StatusFlag.OUT_OF_SERVICE)
        sf_copy.disable(flag=StatusFlag.OVERRIDEN)
        sf_copy.disable(flag=StatusFlag.IN_ALARM)
        return sf_copy


StatusFlags.update_forward_refs()

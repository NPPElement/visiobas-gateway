from copy import copy
from enum import Enum, unique
from typing import Union, Collection

from pydantic import BaseModel, Field, validator


@unique
class StatusFlag(Enum):
    """StatusFlag representation by int."""
    OUT_OF_SERVICE = 0b1000  # принимается ли значения сервером
    OVERRIDEN = 0b0100
    FAULT = 0b0010
    IN_ALARM = 0b0001


class StatusFlags(BaseModel):
    flags: Union['StatusFlags', int, list[int], tuple[int]] = Field(default=0b0000)

    @validator('flags')
    def cast_flags(cls, v: Union[int, Collection[StatusFlag]]) -> int:
        if isinstance(v, (int, StatusFlags)):
            return v.flags
        elif isinstance(v, (list, tuple)):
            sf_int = 0b0000
            v = list(v)

            for i in range(len(v)):
                if v[i]:
                    sf_int |= 1 << len(v) - 1 - i
            return sf_int

    def enable(self, flag: StatusFlag) -> None:
        """Enables flag.

        Args:
            flag: Status flag to enable.
        """
        assert isinstance(flag, StatusFlag)
        self.flags |= flag.value

    def disable(self, flag: StatusFlag) -> None:
        """Disables flag.

        Args:
            flag: Status flag to disable.
        """
        assert isinstance(flag, StatusFlag)
        self.flags &= ~flag.value

    def check(self, flag: StatusFlag) -> bool:
        """Checks the flag is enabled.

        Args:
            flag: Status flag to check.

        Returns:
            True: If flag enabled
            False: If flag disabled.
        """
        assert isinstance(flag, StatusFlag)
        return bool(self.flags & flag.value)

    @property
    def for_http(self) -> 'StatusFlags':
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

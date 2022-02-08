from __future__ import annotations

from enum import Enum, unique
from typing import Iterable

from pydantic import BaseModel, Field, validator


@unique
class StatusFlag(int, Enum):
    """StatusFlag representation by int."""

    # CHANGED = 0b10000
    OUT_OF_SERVICE = 0b1000  # does server receive data?
    FAULT = 0b0100
    OVERRIDEN = 0b0010
    IN_ALARM = 0b0001  # выход за границы приемлемых значений


class StatusFlags(BaseModel):
    """Represent Combination of 4 `StatusFlag`."""

    flags: int = Field(default=0b0000, ge=0, le=15)

    @validator("flags", pre=True)
    def validate_flags(cls, value: int | str | list[StatusFlag]) -> int:
        # pylint: disable=no-self-argument
        if isinstance(value, str):
            return int(value, base=2)
        if isinstance(value, int):
            return value
        if isinstance(value, (list, tuple)) and len(value) == len(StatusFlag):
            sf_int = 0b0000
            for i, flag in enumerate(value):
                if flag:
                    sf_int |= 1 << len(value) - 1 - i
            return sf_int
        raise ValueError("Expected StatusFlags")

    def enable(self, flag: StatusFlag) -> StatusFlags:
        """Enables flag.

        Args:
            flag: Status flag to enable.
        """
        if isinstance(flag, StatusFlag):
            self.flags |= flag.value
            return self
        raise ValueError("StatusFlag expected")

    def disable(self, flag: StatusFlag) -> StatusFlags:
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
        if isinstance(flag, StatusFlag):
            return bool(self.flags & flag.value)
        raise ValueError("StatusFlag expected")

    def get_flags_with_disabled(self, disabled_flags: int) -> StatusFlags:
        """
        Args:
            disabled_flags: Status flags to disable.

        Returns:
            New instance of `StatusFlags`, with disabled flags.
        """
        return StatusFlags(flags=self.flags & ~disabled_flags)

    @classmethod
    def build_status_flags(cls, v: Iterable[int]) -> StatusFlags:
        return StatusFlags(flags=int("".join([str(flag) for flag in v]), base=2))


StatusFlags.update_forward_refs()

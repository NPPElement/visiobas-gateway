from typing import Sequence


class StatusFlags:
    __slots__ = ('in_alarm', 'fault', 'overriden', 'out_of_service')

    # FIXME: Implement singletons

    def __init__(self, status_flags: list = None):
        if status_flags is None:
            self.in_alarm: bool = False
            self.fault: bool = False
            self.overriden: bool = False
            self.out_of_service: bool = False

        elif isinstance(status_flags, Sequence) and len(status_flags) == 4:
            self.in_alarm, self.fault, self.overriden, self.out_of_service = [bool(flag) for
                                                                              flag in
                                                                              status_flags]
        elif isinstance(status_flags, StatusFlags):
            self.in_alarm = status_flags.in_alarm
            self.fault: bool = status_flags.fault
            self.overriden: bool = status_flags.overriden
            self.out_of_service: bool = status_flags.out_of_service

        else:
            raise ValueError('Please, provide <list> with 4 flags or'
                             f'Provided: {status_flags} {type(status_flags)}')

    def __eq__(self, other):
        if isinstance(other, StatusFlags):  # isinstance(self, StatusFlags) and
            return self.as_binary == other.as_binary
        elif isinstance(other, int):  # isinstance(self, StatusFlags) and
            return self.as_binary == other
        elif isinstance(other, str):
            try:
                return self.as_binary == int(other)
            except ValueError:
                return False
        return False

    def __repr__(self) -> str:
        """Convert statusFlags to number by binary coding."""
        return str(self.as_binary)

    @property
    def as_binary(self) -> int:
        return int(''.join([str(int(self.out_of_service)),
                            str(int(self.overriden)),
                            str(int(self.fault)),
                            str(int(self.in_alarm))]), base=2)

    def set(self,
            *,
            in_alarm: bool = None,
            fault: bool = None,
            overriden: bool = None,
            out_of_service: bool = None
            ) -> None:
        if in_alarm is not None:
            if isinstance(in_alarm, bool):
                self.in_alarm = in_alarm
            else:
                raise ValueError(f'Please provide bool value. Provided: {in_alarm}')
        if fault is not None:
            if isinstance(fault, bool):
                self.fault = fault
            else:
                raise ValueError(f'Please provide bool value. Provided: {fault}')
        if overriden is not None:
            if isinstance(overriden, bool):
                self.overriden = overriden
            else:
                raise ValueError(f'Please provide bool value. Provided: {overriden}')
        if out_of_service is not None:
            if isinstance(out_of_service, bool):
                self.out_of_service = out_of_service
            else:
                raise ValueError(f'Please provide bool value. Provided: {out_of_service}')

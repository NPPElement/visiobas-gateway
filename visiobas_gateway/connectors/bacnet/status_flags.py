# todo: change statusFlags list to this class


class StatusFlags:
    def __init__(self, status_flags: list = None):
        if status_flags is None:
            self.in_alarm: bool = False
            self.fault: bool = False
            self.overriden: bool = False
            self.out_of_service: bool = False

        elif isinstance(status_flags, list) and len(status_flags) == 4:
            self.in_alarm, self.fault, self.overriden, self.out_of_service = [bool(flag) for
                                                                              flag in
                                                                              status_flags]
        else:
            raise ValueError('Please, provide list with 4 flags')

    def __repr__(self):
        """Uses to convert into number by binary coding"""
        return str(int(''.join([str(int(self.out_of_service)),
                                str(int(self.overriden)),
                                str(int(self.fault)),
                                str(int(self.in_alarm))]), base=2))

    @property
    def as_binary(self):
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
            self.in_alarm = in_alarm
        if fault is not None:
            self.fault = fault
        if overriden is not None:
            self.overriden = overriden
        if out_of_service is not None:
            self.out_of_service = out_of_service


if __name__ == '__main__':
    sf = StatusFlags()
    sf.set(fault=True)
    print('Fault', sf)
    sf.set(fault=False, overriden=True)
    print('Overriden', sf)
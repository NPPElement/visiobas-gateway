from typing import NamedTuple


class StatusFlags(NamedTuple):
    in_alarm: int
    fault: int
    overriden: int
    out_of_service: int

# todo: change statusFlags list to this class

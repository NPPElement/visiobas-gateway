from enum import Enum, unique


@unique
class Parity(str, Enum):
    """The type of checksum to use to verify data integrity."""

    NONE = "N"
    EVEN = "E"
    ODD = "O"

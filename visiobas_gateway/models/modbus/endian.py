from enum import Enum, unique


@unique
class Endian(str, Enum):
    """Represents the various byte endianess."""

    # This indicates that the bytes are in big endian format
    BIG = ">"

    # This indicates that the bytes are in little endian format
    LITTLE = "<"

    # This indicates that the byte order is chosen by the current native environment.
    AUTO = "@"


def validate_endian(value: str) -> Endian:
    if value in {">", "<", "@"}:
        return Endian(value)
    if isinstance(value, str):
        try:
            return Endian[value.upper()]
        except KeyError:
            pass
    raise ValueError("Invalid Endian")

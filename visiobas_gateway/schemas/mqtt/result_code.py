from enum import IntEnum, unique


@unique
class ResultCode(IntEnum):
    """Represent MQTT result codes."""

    CONNECTION_SUCCESSFUL = 0
    INCORRECT_PROTOCOL_VERSION = 1
    INVALID_CLIENT_IDENTIFIER = 2
    SERVER_UNAVAILABLE = 3
    BAD_USERNAME_OR_PASSWORD = 4
    NOT_AUTHORIZED = 5

    # other currently unused in paho

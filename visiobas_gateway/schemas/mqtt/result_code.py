from enum import Enum, unique


@unique
class ResultCode(int, Enum):
    """Represent MQTT result codes."""

    CONNECTION_SUCCESSFUL = 0
    INCORRECT_PROTOCOL_VERSION = 1
    INVALID_CLIENT_IDENTIFIER = 2
    SERVER_UNAVAILABLE = 3
    BAD_USERNAME_OR_PASSWORD = 4
    NOT_AUTHORIZED = 5

    # other currently unused in paho

    @property
    def result_code(self) -> int:
        return self.value

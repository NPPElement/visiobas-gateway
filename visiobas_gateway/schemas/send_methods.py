from enum import Enum


class SendMethod(str, Enum):
    """Enumeration of all possible ways to send data (clients)."""

    HTTP = "http"
    MQTT = "mqtt"
    # SERIAL = 'serial'

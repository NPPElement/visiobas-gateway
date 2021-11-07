from enum import Enum


class SendMethod(str, Enum):
    HTTP = "http"
    MQTT = "mqtt"
    # SERIAL = 'serial'

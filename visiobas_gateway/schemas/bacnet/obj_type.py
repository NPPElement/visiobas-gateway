from enum import Enum, unique

from .obj_property import ObjProperty


@unique
class ObjType(int, Enum):
    """Supported BACnet object types.

    Enumerated values 0-127 are reserved for definition by ASHRAE.
    Enumerated values 128-1023 may be used by others subject to the procedures and
    constraints
    """

    ANALOG_INPUT = 0
    ANALOG_OUTPUT = 1
    ANALOG_VALUE = 2
    BINARY_INPUT = 3
    BINARY_OUTPUT = 4
    BINARY_VALUE = 5
    CALENDAR = 6
    COMMAND = 7
    DEVICE = 8
    EVENT_ENROLLMENT = 9
    FILE = 10
    GROUP = 11
    LOOP = 12
    MULTI_STATE_INPUT = 13
    MULTI_STATE_OUTPUT = 14
    NOTIFICATION_CLASS = 15
    PROGRAM = 16
    SCHEDULE = 17
    AVERAGING = 18
    MULTI_STATE_VALUE = 19
    TREND_LOG = 20
    LIFE_SAFETY_POINT = 21
    LIFE_SAFETY_ZONE = 22
    ACCUMULATOR = 23
    PULSE_CONVERTER = 24
    EVENT_LOG = 25
    GLOBAL_GROUP = 26
    TREND_LOG_MULTIPLE = 27
    LOAD_CONTROL = 28
    STRUCTURED_VIEW = 29
    ACCESS_DOOR = 30
    # value 31 unassigned
    ACCESS_CREDENTIAL = 32
    ACCESS_POINT = 33
    ACCESS_RIGHTS = 34
    ACCESS_USER = 35
    ACCESS_ZONE = 36
    CREDENTIAL_DATA_INPUT = 37
    NETWORK_SECURITY = 38
    BITSTRING_VALUE = 39
    CHARACTERSTRING_VALUE = 40
    DATE_PATTERN_VALUE = 41
    DATE_VALUE = 42
    DATETIME_PATTERN_VALUE = 43
    DATETIME_VALUE = 44
    INTEGER_VALUE = 45
    LARGE_ANALOG_VALUE = 46
    OCTETSTRING_VALUE = 47
    POSITIVE_INTEGER_VALUE = 48
    TIME_PATTERN_VALUE = 49
    TIME_VALUE = 50
    NOTIFICATION_FORWARDER = 51
    ALERT_ENROLLMENT = 52
    CHANNEL = 53
    LIGHTING_OUTPUT = 54

    # TODO: add JSON-input = 250
    # TODO: add JSON-output = 251

    @property
    def type_id(self) -> int:
        return self.value


ANALOG_TYPES = {
    ObjType.ANALOG_INPUT,
    ObjType.ANALOG_OUTPUT,
    ObjType.ANALOG_VALUE,
}
BINARY_TYPES = {
    ObjType.BINARY_INPUT,
    ObjType.BINARY_VALUE,
    ObjType.BINARY_OUTPUT,
}

DISCRETE_TYPES = {
    ObjType.BINARY_INPUT,
    ObjType.BINARY_VALUE,
    ObjType.BINARY_OUTPUT,
    ObjType.MULTI_STATE_INPUT,
    ObjType.MULTI_STATE_OUTPUT,
    ObjType.MULTI_STATE_VALUE,
}

INPUT_TYPES = {
    ObjType.BINARY_INPUT,
    ObjType.ANALOG_INPUT,
    ObjType.MULTI_STATE_INPUT,
}
OUTPUT_TYPES = {
    ObjType.BINARY_OUTPUT,
    ObjType.BINARY_VALUE,
    ObjType.ANALOG_OUTPUT,
    ObjType.ANALOG_VALUE,
    ObjType.MULTI_STATE_VALUE,
    ObjType.MULTI_STATE_OUTPUT,
}
INPUT_PROPERTIES = (ObjProperty.PRESENT_VALUE, ObjProperty.STATUS_FLAGS)
OUTPUT_PROPERTIES = (
    ObjProperty.PRESENT_VALUE,
    ObjProperty.STATUS_FLAGS,
    ObjProperty.PRIORITY_ARRAY,
)
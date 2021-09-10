from enum import Enum, unique


@unique
class Reliability(int, Enum):
    NO_FAULT_DETECTED = 0
    NO_SENSOR = 1
    OVER_RANGE = 2
    UNDER_RANGE = 3
    OPEN_LOOP = 4
    SHORTED_LOOP = 5
    NO_OUTPUT = 6
    UNRELIABLE_OTHER = 7
    PROCESS_ERROR = 8
    MULTI_STATE_FAULT = 9
    CONFIGURATION_ERROR = 10
    # enumeration value 11 is reserved for a future addendum
    COMMUNICATION_FAILURE = 12
    MEMBER_FAULT = 13
    MONITORED_OBJECT_FAULT = 14
    TRIPPED = 15


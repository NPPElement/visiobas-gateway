from enum import Enum, unique


@unique
class Qos(Enum):
    """Quality of Service levels"""
    AT_MOST_ONCE_DELIVERY = 0
    AT_LEAST_ONCE_DELIVERY = 1
    EXACTLY_ONCE_DELIVERY = 2

from enum import Enum, unique


@unique
class Protocol(Enum):
    BACNET = 'BACnet'
    MODBUS_TCP = 'ModbusTCP'
    MODBUS_RTU = 'ModbusRTU'

    def __new__(cls, *values):
        obj = object.__new__(cls)
        for other_value in values:
            cls._value2member_map_[other_value] = obj
        obj._all_values = values
        return obj

    def __repr__(self) -> str:
        return self.value

    # @property
    # def name(self) -> str:
    #     return self.value

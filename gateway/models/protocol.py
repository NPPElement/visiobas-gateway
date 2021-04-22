from enum import Enum, unique


@unique
class Protocol(Enum):
    BACNET = 'BACnet'
    MODBUS_TCP = 'ModbusTCP'
    MODBUS_RTU = 'ModbusRTU'

    def __repr__(self) -> str:
        return self.value

    # @property
    # def name(self) -> str:
    #     return self.value

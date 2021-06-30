from enum import Enum, unique


@unique
class Protocol(Enum):
    BACNET = 'BACnet'
    MODBUS_TCP = 'ModbusTCP'
    MODBUS_RTU = 'ModbusRTU'
    MODBUS_RTUOVERTCP = 'ModbusRTUoverTCP'
    SUNAPI = 'SUNAPI'

    def __new__(cls, *values):
        obj = object.__new__(cls)
        for other_value in values:
            cls._value2member_map_[other_value] = obj
        obj._all_values = values
        return obj

    def __repr__(self) -> str:
        return self.value

    @property
    def is_camera(self) -> bool:
        return True if self is Protocol.SUNAPI else False

    @property
    def is_polling_device(self) -> bool:
        polling_protocols = {Protocol.BACNET, Protocol.MODBUS_TCP,
                             Protocol.MODBUS_RTU, Protocol.MODBUS_RTUOVERTCP, }
        return True if self in polling_protocols else False



    # @property
    # def name(self) -> str:
    #     return self.value

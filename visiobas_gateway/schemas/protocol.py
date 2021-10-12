from enum import Enum, unique


@unique
class Protocol(str, Enum):
    """Supported devices protocols."""

    BACNET = "BACnet"
    MODBUS_TCP = "ModbusTCP"
    MODBUS_RTU = "ModbusRTU"
    MODBUS_RTU_OVER_TCP = "ModbusRTUoverTCP"
    # SUN_API = "SUNAPI"


POLLING_PROTOCOLS = {
    Protocol.BACNET,
    Protocol.MODBUS_TCP,
    Protocol.MODBUS_RTU,
    Protocol.MODBUS_RTU_OVER_TCP,
}
# CAMERA_PROTOCOLS = {
#     Protocol.SUN_API,
# }
TCP_IP_PROTOCOLS = {
    Protocol.BACNET,
    Protocol.MODBUS_TCP,
    Protocol.MODBUS_RTU_OVER_TCP,
    # Protocol.SUN_API,
}
SERIAL_PROTOCOLS = {Protocol.MODBUS_RTU}

MODBUS_TCP_IP_PROTOCOLS = {
    Protocol.MODBUS_TCP,
    Protocol.MODBUS_RTU_OVER_TCP,
}

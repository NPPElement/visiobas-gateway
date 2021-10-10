from visiobas_gateway.schemas.bacnet.device_property_list import (
    TcpDevicePropertyList,
)
from visiobas_gateway.schemas.modbus.device_property_list import (
    SerialDevicePropertyList,
    ModbusTcpDevicePropertyList,
)


class TestDeviceObj:
    def test_construct_happy(
        self, tcp_device_factory, serial_device_factory, modbus_tcp_device_factory
    ):
        tcp_ip_device_obj = tcp_device_factory()
        assert isinstance(tcp_ip_device_obj.property_list, TcpDevicePropertyList)

        serial_device_obj = serial_device_factory()
        assert isinstance(serial_device_obj.property_list, SerialDevicePropertyList)

        tcp_ip_modbus_device_obj = modbus_tcp_device_factory()
        assert isinstance(
            tcp_ip_modbus_device_obj.property_list, ModbusTcpDevicePropertyList
        )

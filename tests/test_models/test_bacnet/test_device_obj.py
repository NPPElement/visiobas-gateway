from gateway.models.bacnet.device_property_list import (
    TcpIpDevicePropertyList,
    SerialDevicePropertyList,
)


class TestDeviceObj:
    def test_construct_happy(self, tcp_ip_device_factory, serial_device_factory):
        tcp_ip_device_obj = tcp_ip_device_factory()
        assert isinstance(tcp_ip_device_obj.property_list, TcpIpDevicePropertyList)

        serial_device_obj = serial_device_factory()
        assert isinstance(serial_device_obj.property_list, SerialDevicePropertyList)

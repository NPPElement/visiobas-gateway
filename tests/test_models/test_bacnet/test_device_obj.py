import pydantic
import pytest


class TestDevicePropertyListRTU:
    def test_construct_happy(self, device_property_list_rtu_factory):
        rtu_properties = device_property_list_rtu_factory()
        assert rtu_properties.port == "/dev/ttyS0"
        assert rtu_properties.unit == 10
        assert rtu_properties.baudrate == 9600
        assert rtu_properties.stopbits == 1
        assert rtu_properties.bytesize == 8
        assert rtu_properties.parity == "N"

    def test_bad_baudrate(self, device_property_list_rtu_factory):
        with pytest.raises(pydantic.ValidationError):
            device_property_list_rtu_factory(baudrate=13)

    def test_bad_parity(self, device_property_list_rtu_factory):
        with pytest.raises(pydantic.ValidationError):
            device_property_list_rtu_factory(parity="bad_parity")


class TestDevicePropertyList:
    def test_construct_happy(self, device_property_list_tcp_ip_factory):
        tcp_ip_property_list = device_property_list_tcp_ip_factory()
        assert tcp_ip_property_list.port == 502
        assert tcp_ip_property_list.protocol == 10
        assert tcp_ip_property_list.timeout == 9600
        assert tcp_ip_property_list.retries == 1
        assert tcp_ip_property_list.bytesize == 8
        assert tcp_ip_property_list.parity == "N"

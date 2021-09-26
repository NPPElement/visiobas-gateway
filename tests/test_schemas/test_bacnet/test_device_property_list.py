import pydantic
import pytest

from visiobas_gateway.schemas import Protocol


class TestBaseDevicePropertyList:
    def test_construct_happy(self, device_base_property_list_factory):
        base_device_property_list = device_base_property_list_factory()
        assert base_device_property_list.protocol == Protocol.BACNET
        assert base_device_property_list.timeout == 500
        assert base_device_property_list.retries == 3
        assert base_device_property_list.send_period == 300
        assert base_device_property_list.poll_period == 90
        assert base_device_property_list.reconnect_period == 300


class TestTcpIpDevicePropertyList:
    def test_construct_happy(self, tcp_ip_device_property_list_factory):
        tcp_ip_device_property_list = tcp_ip_device_property_list_factory(
            apduTimeout=10_000, numberOfApduRetries=2
        )
        assert tcp_ip_device_property_list.protocol == Protocol.BACNET
        assert tcp_ip_device_property_list.timeout == 10_000
        assert tcp_ip_device_property_list.retries == 2
        assert tcp_ip_device_property_list.send_period == 300
        assert tcp_ip_device_property_list.poll_period == 90
        assert tcp_ip_device_property_list.reconnect_period == 300

        assert str(tcp_ip_device_property_list.address) == "10.21.10.21"
        assert tcp_ip_device_property_list.port == 47808

    @pytest.mark.parametrize(
        "bad_protocol",
        ["ModbusRTU", "ModbusRTUoverTCP", "ModbusTCP", "SunAPI"],
    )
    def test_construct_bad_protocol(
        self, tcp_ip_device_property_list_factory, bad_protocol
    ):
        with pytest.raises(pydantic.ValidationError):
            tcp_ip_device_property_list_factory(protocol=bad_protocol)


class TestSerialDevicePropertyList:
    def test_construct_happy(self, serial_device_property_list_factory):
        from visiobas_gateway.schemas.modbus.device_rtu_properties import (
            DeviceRtuProperties,
        )

        serial_device_property_list = serial_device_property_list_factory()
        assert serial_device_property_list.protocol == Protocol.MODBUS_RTU
        assert serial_device_property_list.timeout == 6_000
        assert serial_device_property_list.retries == 3

        assert isinstance(serial_device_property_list.rtu, DeviceRtuProperties)
        assert serial_device_property_list.rtu.baudrate == 9_600

    @pytest.mark.parametrize(
        "bad_protocol",
        ["ModbusRTUoverTCP", "ModbusTCP", "SunAPI", "BACnet"],
    )
    def test_construct_bad_protocol(
        self, serial_device_property_list_factory, bad_protocol
    ):
        with pytest.raises(pydantic.ValidationError):
            serial_device_property_list_factory(protocol=bad_protocol)


class TestTcpIpModbusDevicePropertyList:
    def test_construct_happy(self, tcp_ip_modbus_device_property_list_factory):
        tcp_ip_modbus_device_property_list = tcp_ip_modbus_device_property_list_factory(
            apduTimeout=10_000, numberOfApduRetries=2
        )
        assert tcp_ip_modbus_device_property_list.protocol == Protocol.MODBUS_RTU_OVER_TCP
        assert tcp_ip_modbus_device_property_list.timeout == 10_000
        assert tcp_ip_modbus_device_property_list.retries == 2
        assert tcp_ip_modbus_device_property_list.send_period == 300
        assert tcp_ip_modbus_device_property_list.poll_period == 90
        assert tcp_ip_modbus_device_property_list.reconnect_period == 300

        assert str(tcp_ip_modbus_device_property_list.address) == "10.21.10.21"
        assert tcp_ip_modbus_device_property_list.port == 502

        assert tcp_ip_modbus_device_property_list.rtu.unit == 1

    @pytest.mark.parametrize(
        "bad_protocol",
        ["ModbusRTU", "BACnet", "SunAPI"],
    )
    def test_construct_bad_protocol(
        self, tcp_ip_modbus_device_property_list_factory, bad_protocol
    ):
        with pytest.raises(pydantic.ValidationError):
            tcp_ip_modbus_device_property_list_factory(protocol=bad_protocol)

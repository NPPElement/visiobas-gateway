import pytest
from visiobas_gateway.schemas.protocol import Protocol
from pydantic import ValidationError
from visiobas_gateway.schemas.modbus.device_rtu_properties import DeviceRtuProperties


# TODO: move to modbus + refactor (see example above)
class TestSerialDevicePropertyList:
    @pytest.mark.parametrize(
        "data, rtu",
        ["ModbusRTUoverTCP", "ModbusTCP", "SunAPI", "BACnet"],
    )
    def test_construct_happy(self, serial_device_property_list_factory):

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
        with pytest.raises(ValidationError):
            serial_device_property_list_factory(protocol=bad_protocol)


class TestModbusTcpDevicePropertyList:
    def test_construct_happy(self, modbus_tcp_device_property_list_factory):
        tcp_ip_modbus_device_property_list = modbus_tcp_device_property_list_factory(
            apduTimeout=10_000, numberOfApduRetries=2
        )
        assert tcp_ip_modbus_device_property_list.protocol == Protocol.MODBUS_TCP
        assert tcp_ip_modbus_device_property_list.timeout == 10_000
        assert tcp_ip_modbus_device_property_list.retries == 2
        assert tcp_ip_modbus_device_property_list.send_period == 300
        assert tcp_ip_modbus_device_property_list.poll_period == 90
        assert tcp_ip_modbus_device_property_list.reconnect_period == 300

        assert str(tcp_ip_modbus_device_property_list.ip) == "10.21.10.21"
        assert tcp_ip_modbus_device_property_list.port == 502

        assert tcp_ip_modbus_device_property_list.rtu.unit == 1

    @pytest.mark.parametrize(
        "bad_protocol",
        ["ModbusRTU", "BACnet", "SunAPI"],
    )
    def test_construct_bad_protocol(
        self, modbus_tcp_device_property_list_factory, bad_protocol
    ):
        with pytest.raises(ValidationError):
            modbus_tcp_device_property_list_factory(protocol=bad_protocol)

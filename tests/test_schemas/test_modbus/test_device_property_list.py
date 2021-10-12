import pytest
from visiobas_gateway.schemas.protocol import Protocol
from pydantic import ValidationError
from visiobas_gateway.schemas.modbus.device_rtu_properties import (
    DeviceRtuProperties,
    BaseDeviceModbusProperties,
)
from visiobas_gateway.schemas.modbus.device_property_list import SerialDevicePropertyList


class TestModbusTcpDevicePropertyList:
    @pytest.mark.parametrize(
        "data, expected_rtu",
        [
            ({"unit": 0x02}, BaseDeviceModbusProperties(unit=2)),
            ({}, BaseDeviceModbusProperties(unit=0x01)),
        ],
    )
    def test_construct_happy(
        self, modbus_tcp_device_property_list_factory, data, expected_rtu
    ):
        modbus_tcp_device_property_list = modbus_tcp_device_property_list_factory(**data)
        assert modbus_tcp_device_property_list.rtu == expected_rtu

    @pytest.mark.parametrize(
        "bad_protocol",
        ["ModbusRTU", "BACnet", "SunAPI"],
    )
    def test_construct_bad_protocol(
        self, modbus_tcp_device_property_list_factory, bad_protocol
    ):
        with pytest.raises(ValidationError):
            modbus_tcp_device_property_list_factory(protocol=bad_protocol)


class TestSerialDevicePropertyList:
    def test_construct_happy(self, serial_device_property_list_factory):
        serial_device_property_list = serial_device_property_list_factory()
        assert isinstance(serial_device_property_list, SerialDevicePropertyList)
        assert isinstance(serial_device_property_list.rtu, DeviceRtuProperties)
        assert serial_device_property_list.protocol == Protocol.MODBUS_RTU
        assert serial_device_property_list.timeout == 6_000
        assert serial_device_property_list.retries == 3
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

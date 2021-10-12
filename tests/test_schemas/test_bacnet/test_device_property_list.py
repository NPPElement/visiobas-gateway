from ipaddress import IPv4Address

import pydantic
import pytest
from pydantic import ValidationError

from visiobas_gateway.schemas import Protocol
from visiobas_gateway.schemas.bacnet.device_property_list import BaseDevicePropertyList


class TestBaseDevicePropertyList:
    @pytest.mark.parametrize(
        "data, expected_protocol, expected_timeout, expected_retries, "
        "expected_send_period, expected_reconnect_period",
        [
            ({}, Protocol.BACNET, 500, 3, 300, 300),
            (
                {
                    "protocol": "ModbusTCP",
                    "apduTimeout": 10_000,
                    "numberOfApduRetries": 2,
                    "sendPeriod": 60,
                    "reconnectPeriod": 600,
                },
                Protocol.MODBUS_TCP,
                10_000,
                2,
                60,
                600,
            ),
        ],
    )
    def test_construct_happy(
        self,
        device_base_property_list_factory,
        data,
        expected_protocol,
        expected_timeout,
        expected_retries,
        expected_send_period,
        expected_reconnect_period,
    ):
        base_device_property_list = device_base_property_list_factory(**data)

        assert isinstance(base_device_property_list, BaseDevicePropertyList)
        assert base_device_property_list.protocol == expected_protocol
        assert base_device_property_list.timeout == expected_timeout
        assert base_device_property_list.retries == expected_retries
        assert base_device_property_list.send_period == expected_send_period
        # assert base_device_property_list.poll_period == 90
        assert base_device_property_list.reconnect_period == expected_reconnect_period

        expected_timeout_seconds = expected_timeout / 1000
        assert base_device_property_list.timeout_seconds == expected_timeout_seconds

        assert hasattr(base_device_property_list, "interface")

    @pytest.mark.parametrize(
        "data",
        [
            {"apduTimeout": "bad_timeout"},
            {"apduTimeout": 0},
            {"apduTimeout": "-1"},
            {"apduTimeout": 60_000},
        ],
    )
    def test_timeout_bad(self, device_base_property_list_factory, data):
        with pytest.raises(ValidationError):
            device_base_property_list_factory(**data)

    @pytest.mark.parametrize(
        "data",
        [
            {"numberOfApduRetries": "bad_timeout"},
            {"numberOfApduRetries": "-1"},
            {"numberOfApduRetries": 4},
        ],
    )
    def test_retries_bad(self, device_base_property_list_factory, data):
        with pytest.raises(ValidationError):
            device_base_property_list_factory(**data)

    @pytest.mark.parametrize(
        "data",
        [
            {"sendPeriod": "bad_send_period"},
            {"sendPeriod": "-1"},
        ],
    )
    def test_send_period_bad(self, device_base_property_list_factory, data):
        with pytest.raises(ValidationError):
            device_base_property_list_factory(**data)

    @pytest.mark.parametrize(
        "data",
        [
            {"reconnectPeriod": "bad_reconnect_period"},
            {"reconnectPeriod": -1},
        ],
    )
    def test_reconnect_period_bad(self, device_base_property_list_factory, data):
        with pytest.raises(ValidationError):
            device_base_property_list_factory(**data)


class TestTcpDevicePropertyList:
    @pytest.mark.parametrize(
        "data, expected_protocol, expected_ip, expected_port",
        [
            ({}, Protocol.BACNET, IPv4Address("10.21.10.21"), 47808),
            (
                {"port": 0xBAC2, "address": "10.21.10.13"},
                Protocol.BACNET,
                IPv4Address("10.21.10.13"),
                47810,
            ),
        ],
    )
    def test_construct_happy(
        self,
        tcp_device_property_list_factory,
        data,
        expected_protocol,
        expected_ip,
        expected_port,
    ):
        tcp_device_property_list = tcp_device_property_list_factory(**data)
        assert tcp_device_property_list.protocol == expected_protocol
        assert tcp_device_property_list.ip == expected_ip
        assert tcp_device_property_list.port == expected_port
        assert tcp_device_property_list.interface == (expected_ip, expected_port)

    @pytest.mark.parametrize(
        "bad_protocol",
        ["ModbusRTU", "ModbusRTUoverTCP", "ModbusTCP", "SunAPI"],
    )
    def test_construct_bad_protocol(self, tcp_device_property_list_factory, bad_protocol):
        with pytest.raises(pydantic.ValidationError):
            tcp_device_property_list_factory(protocol=bad_protocol)

    @pytest.mark.parametrize(
        "bad_port",
        ["-1", "bad_port", 99_999],
    )
    def test_construct_bad_port(self, tcp_device_property_list_factory, bad_port):
        with pytest.raises(pydantic.ValidationError):
            tcp_device_property_list_factory(protocol=bad_port)


# TODO: move to modbus + refactor (see example above)
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
        with pytest.raises(pydantic.ValidationError):
            modbus_tcp_device_property_list_factory(protocol=bad_protocol)

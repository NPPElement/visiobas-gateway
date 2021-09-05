from typing import Callable, Any

from gateway.models.bacnet.base_obj import BaseBACnetObj
from gateway.models.bacnet.device_property_list import (
    BaseDevicePropertyList,
    TcpIpDevicePropertyList,
    SerialDevicePropertyList,
)
from gateway.models.modbus.device_rtu_properties import DeviceRtuProperties

from gateway.models.bacnet.device_obj import DeviceObj

import pytest


@pytest.fixture
def base_bacnet_obj_factory() -> Callable[..., BaseBACnetObj]:
    """
    Produces `BaseBACnetObj` for tests.

    You can pass the same params into this as the `BaseBACnetObj` constructor to
    override defaults.
    """

    def _factory(**kwargs):
        kwargs = _base_bacnet_obj_kwargs(kwargs)
        return BaseBACnetObj(**kwargs)

    return _factory


@pytest.fixture
def device_rtu_properties_factory() -> Callable[..., DeviceRtuProperties]:
    """
    Produces `DeviceRtuProperties` for tests.

    You can pass the same params into this as the `DeviceRtuProperties` constructor to
    override defaults.
    """

    def _factory(**kwargs):
        kwargs = _device_rtu_properties_kwargs(kwargs)
        return DeviceRtuProperties(**kwargs)

    return _factory


@pytest.fixture
def device_base_property_list_factory() -> Callable[..., BaseDevicePropertyList]:
    """
    Produces `BaseDevicePropertyList` for tests.

    You can pass the same params into this as the `BaseDevicePropertyList` constructor to
    override defaults.
    """

    def _factory(**kwargs):
        kwargs = _base_device_property_list_kwargs(kwargs)
        return BaseDevicePropertyList(**kwargs)

    return _factory


@pytest.fixture
def tcp_ip_device_property_list_factory() -> Callable[..., TcpIpDevicePropertyList]:
    """
    Produces `TcpIpDevicePropertyList` for tests.

    You can pass the same params into this as the `TcpIpDevicePropertyList` constructor to
    override defaults.
    """

    def _factory(**kwargs):
        kwargs = _tcp_ip_device_property_list_kwargs(kwargs)
        return TcpIpDevicePropertyList(**kwargs)

    return _factory


@pytest.fixture
def serial_device_property_list_factory() -> Callable[..., SerialDevicePropertyList]:
    """
    Produces `SerialDevicePropertyList` for tests.

    You can pass the same params into this as the `SerialDevicePropertyList` constructor to
    override defaults.
    """

    def _factory(**kwargs):
        kwargs = _serial_device_property_list_kwargs(kwargs)
        return SerialDevicePropertyList(**kwargs)

    return _factory


@pytest.fixture
def tcp_ip_device_factory() -> Callable[..., DeviceObj]:
    """
    Produces `DeviceObj` with `TcpIpDevicePropertyList` for tests.

    You can pass the same params into this as the `DeviceObj` constructor to
    override defaults.
    """

    def _factory(**kwargs):
        kwargs = _tcp_ip_device_obj_kwargs(kwargs)
        return DeviceObj(**kwargs)

    return _factory


@pytest.fixture
def serial_device_factory() -> Callable[..., DeviceObj]:
    """
    Produces `DeviceObj` with `SerialDevicePropertyList` for tests.

    You can pass the same params into this as the `DeviceObj` constructor to
    override defaults.
    """

    def _factory(**kwargs):
        kwargs = _serial_device_obj_kwargs(kwargs)
        return DeviceObj(**kwargs)

    return _factory


def _base_bacnet_obj_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    kwargs = {
        "75": 75,
        "77": "Name:Name/Name.Name",
        "79": "analog-input",
        "371": {
            "template": "",
            "alias": "",
            "replace": {},
        },
        "846": 846,
        **kwargs,
    }
    return kwargs


def _device_rtu_properties_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    kwargs = {
        "unit": 10,
        "port": "/dev/ttyS0",
        "baudrate": 9600,
        "stopbits": 1,
        "bytesize": 8,
        "parity": "N",
        **kwargs,
    }
    return kwargs


def _base_device_property_list_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    kwargs = {
        "template": "",
        "alias": "",
        "replace": {},
        "protocol": "BACnet",
        "apduTimeout": 500,
        "numberOfApduRetries": 3,
        **kwargs,
    }
    return kwargs


def _tcp_ip_device_property_list_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    kwargs = {
        "template": "",
        "alias": "",
        "replace": {},
        "address": "10.21.10.21",
        "port": 502,
        "protocol": "ModbusTCP",
        "timeout": 500,
        "retries": 3,
        **kwargs,
    }
    return kwargs


def _serial_device_property_list_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    kwargs = {
        "template": "",
        "alias": "",
        "replace": {},
        "protocol": "ModbusRTU",
        "rtu": _device_rtu_properties_kwargs({}),
        **kwargs,
    }
    return kwargs


def _tcp_ip_device_obj_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    kwargs = {
        **_base_bacnet_obj_kwargs({}),
        "371": _tcp_ip_device_property_list_kwargs({}),
        **kwargs,
    }
    return kwargs


def _serial_device_obj_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    kwargs = {
        **_base_bacnet_obj_kwargs({}),
        "371": _serial_device_property_list_kwargs({}),
        **kwargs,
    }
    return kwargs


# kwargs = {
#          '371': '{"template":"","alias":"","replace":{},"address":"10.21.80.209","port":502,"protocol":"ModbusTCP","apduTimeout":500,"numberOfApduRetries":3}',
#
#          '73': 10,
#          '75': 86266,
#          '76': None,
#          '77': 'Name:NAME_name',
#          '79': 'device',
#          '846': 86266,
#     }

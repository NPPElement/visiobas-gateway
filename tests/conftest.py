from typing import Callable, Any

from gateway.models.bacnet.base_obj import BaseBACnetObj
from gateway.models.bacnet.device_property_list import BaseDevicePropertyList
from gateway.models.modbus.rtu_properties import RtuProperties

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
def device_property_list_rtu_factory() -> Callable[..., RtuProperties]:
    """
    Produces `DevicePropertyListRTU` for tests.

    You can pass the same params into this as the `DevicePropertyListRTU` constructor to
    override defaults.
    """

    def _factory(**kwargs):
        kwargs = _base_rtu_properties_kwargs(kwargs)
        return RtuProperties(**kwargs)

    return _factory


@pytest.fixture
def device_property_list_tcp_ip_factory() -> Callable[..., BaseDevicePropertyList]:
    """
    Produces `DevicePropertyList` for tests.

    You can pass the same params into this as the `DevicePropertyList` constructor to
    override defaults.
    """

    def _factory(**kwargs):
        kwargs = _base_device_property_list_tcp_ip_kwargs(kwargs)
        return BaseDevicePropertyList(**kwargs)

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


def _base_rtu_properties_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
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


def _base_device_property_list_tcp_ip_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    kwargs = {
        "template": "",
        "alias": "",
        "replace": {},
        "address": "10.21.80.209",
        "port": 502,
        "protocol": "ModbusTCP",
        "timeout": 500,
        "retries": 3,
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

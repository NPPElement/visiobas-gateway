import json
from typing import Callable, Any

from visiobas_gateway.schemas.bacnet.base_obj import BaseBACnetObj
from visiobas_gateway.schemas.bacnet.device_property_list import (
    BaseDevicePropertyList,
    TcpDevicePropertyList,
)
from visiobas_gateway.schemas.modbus.device_property_list import (
    SerialDevicePropertyList,
    ModbusTcpDevicePropertyList,
)
from visiobas_gateway.schemas.modbus.device_rtu_properties import (
    DeviceRtuProperties,
    BaseDeviceModbusProperties,
)
from visiobas_gateway.schemas.modbus.modbus_properties import ModbusProperties

from visiobas_gateway.schemas.bacnet.device_obj import DeviceObj
from visiobas_gateway.schemas.bacnet.obj import BACnetObj
from visiobas_gateway.api.jsonrpc.schemas import JsonRPCSetPointParams
from visiobas_gateway.devices.base_device import BaseDevice
from visiobas_gateway.gateway import Gateway
from visiobas_gateway.schemas.settings.gateway_settings import GatewaySettings
from visiobas_gateway.schemas.bacnet.obj_property_list import BaseBACnetObjPropertyList
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
def base_device_modbus_properties() -> Callable[..., BaseDeviceModbusProperties]:
    """
    Produces `BaseDeviceModbusProperties` for tests.

    You can pass the same params into this as the `BaseDeviceModbusProperties` constructor to
    override defaults.
    """

    def _factory(**kwargs):
        kwargs = _base_device_modbus_properties_kwargs(kwargs)
        return BaseDeviceModbusProperties(**kwargs)

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

    class ForTestBaseDevicePropertyList(BaseDevicePropertyList):
        """Class for inheriting from ABC + with abstract method implementation."""

        def interface(self) -> Any:
            pass

    def _factory(**kwargs):
        kwargs = _base_device_property_list_kwargs(kwargs)
        return ForTestBaseDevicePropertyList(**kwargs)

    return _factory


@pytest.fixture
def base_obj_property_list_factory() -> Callable[..., BaseBACnetObjPropertyList]:
    """
    Produces `BaseBACnetObjPropertyList` for tests.

    You can pass the same params into this as the `BaseBACnetObjPropertyList` constructor to
    override defaults.
    """

    class ForTestBaseBACnetObjPropertyList(BaseBACnetObjPropertyList):
        """Class for inheriting from ABC."""

    def _factory(**kwargs):
        kwargs = _base_obj_property_list_kwargs(kwargs)
        return ForTestBaseBACnetObjPropertyList(**kwargs)

    return _factory


@pytest.fixture
def tcp_device_property_list_factory() -> Callable[..., TcpDevicePropertyList]:
    """
    Produces `TcpDevicePropertyList` for tests.

    You can pass the same params into this as the `TcpDevicePropertyList` constructor to
    override defaults.
    """

    def _factory(**kwargs):
        kwargs = _tcp_device_property_list_kwargs(kwargs)
        return TcpDevicePropertyList(**kwargs)

    return _factory


@pytest.fixture
def modbus_tcp_device_property_list_factory() -> Callable[..., ModbusTcpDevicePropertyList]:
    """
    Produces `ModbusTcpDevicePropertyList` for tests.

    You can pass the same params into this as the `ModbusTcpDevicePropertyList`
    constructor to override defaults.
    """

    def _factory(**kwargs):
        kwargs = _modbus_tcp_device_property_list_kwargs(kwargs)
        return ModbusTcpDevicePropertyList(**kwargs)

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
def tcp_device_obj_factory() -> Callable[..., DeviceObj]:
    """
    Produces `DeviceObj` with `TcpIpDevicePropertyList` for tests.

    You can pass the same params into this as the `DeviceObj` constructor to
    override defaults.
    """

    def _factory(**kwargs):
        kwargs = _tcp_device_obj_kwargs(kwargs)
        return DeviceObj(**kwargs)

    return _factory


@pytest.fixture
def modbus_tcp_device_obj_factory() -> Callable[..., DeviceObj]:
    """
    Produces `DeviceObj` with `TcpIpDevicePropertyList` for tests.

    You can pass the same params into this as the `DeviceObj` constructor to
    override defaults.
    """

    def _factory(**kwargs):
        kwargs = _modbus_tcp_device_obj_kwargs(kwargs)
        return DeviceObj(**kwargs)

    return _factory


@pytest.fixture
def serial_device_obj_factory() -> Callable[..., DeviceObj]:
    """
    Produces `DeviceObj` with `SerialDevicePropertyList` for tests.

    You can pass the same params into this as the `DeviceObj` constructor to
    override defaults.
    """

    def _factory(**kwargs):
        kwargs = _serial_device_obj_kwargs(kwargs)
        return DeviceObj(**kwargs)

    return _factory


@pytest.fixture
def base_device_factory() -> Callable[..., BaseDevice]:
    """
    Produces `BaseDevice` with `DeviceObj` for tests.

    You can pass the same params into this as the `BaseDevice` constructor to
    override defaults.
    """

    def _factory(**kwargs):
        kwargs = _base_device_kwargs(kwargs)
        return BaseDevice(**kwargs)

    return _factory


@pytest.fixture
async def gateway_factory() -> Callable[..., Gateway]:
    """
    Produces `Gateway` for tests.

    You can pass the same params into this as the `Gateway` constructor to
    override defaults.
    """

    def _factory(**kwargs):
        kwargs = _gateway_kwargs(kwargs)
        return Gateway(**kwargs)

    return _factory


@pytest.fixture
def modbus_properties_factory() -> Callable[..., ModbusProperties]:
    """
    Produces `ModbusProperties` for tests.

    You can pass the same params into this as the `ModbusProperties` constructor to
    override defaults.
    """

    def _factory(**kwargs):
        kwargs = _modbus_properties_kwargs(kwargs)
        return ModbusProperties(**kwargs)

    return _factory


@pytest.fixture
def bacnet_obj_factory() -> Callable[..., BACnetObj]:
    """
    Produces `BACnetObj` for tests.

    You can pass the same params into this as the `BACnetObj` constructor to
    override defaults.
    """

    def _factory(**kwargs):
        kwargs = _bacnet_obj_kwargs(kwargs)
        return BACnetObj(**kwargs)

    return _factory


@pytest.fixture
def json_rpc_set_point_params_factory() -> Callable[..., JsonRPCSetPointParams]:
    """
    Produces `JsonRPCSetPointParams` for tests.

    You can pass the same params into this as the `JsonRPCSetPointParams` constructor to
    override defaults.
    """

    def _factory(**kwargs):
        kwargs = _jsonrpc_set_point_params(kwargs)
        return JsonRPCSetPointParams(**kwargs)

    return _factory


@pytest.fixture
def gateway_settings_factory() -> Callable[..., GatewaySettings]:
    """
    Produces `GatewaySettings` for tests.

    You can pass the same params into this as the `GatewaySettings` constructor to
    override defaults.
    """

    def _factory(**kwargs):
        kwargs = _gateway_settings_kwargs(kwargs)
        return GatewaySettings(**kwargs)

    return _factory


def _gateway_settings_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    kwargs = {
        "update_period": 3600,
        "unreachable_reset_period": 1800,
        "unreachable_threshold": 3,
        "override_threshold": 8,
        "poll_device_ids": [11, 22, 33],
        **kwargs,
    }
    return kwargs


def _base_device_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    kwargs = {
        "gateway": Gateway(**_gateway_kwargs(kwargs)),
        "device_obj": DeviceObj(**_serial_device_obj_kwargs(kwargs)),
        **kwargs,
    }
    return kwargs


def _gateway_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    kwargs = {
        "gateway_settings": GatewaySettings(**_gateway_settings_kwargs(kwargs)),
        "api_settings": None,  # todo
        "http_settings": None,
        "mqtt_settings": None,
        **kwargs,
    }
    return kwargs


def _base_bacnet_obj_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    kwargs = {
        "75": 75,
        "77": "Name:Name/Name.Name",
        "79": "analog-input",
        "371": json.dumps(
            {
                "template": "",
                "alias": "",
                "replace": {},
            }
        ),
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


def _base_device_modbus_properties_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    kwargs = {
        "unit": 1,
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


def _base_obj_property_list_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    kwargs = {
        "poll_period": 90,
        **kwargs,
    }
    return kwargs


def _tcp_device_property_list_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    kwargs = {
        "template": "",
        "alias": "",
        "replace": {},
        "address": "10.21.10.21",
        "port": 0xBAC0,
        "protocol": "BACnet",
        "timeout": 500,
        "retries": 3,
        **kwargs,
    }
    return kwargs


def _modbus_tcp_device_property_list_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    kwargs = {
        "template": "",
        "alias": "",
        "replace": {},
        "address": "10.21.10.21",
        "port": 502,
        "protocol": "ModbusTCP",
        "timeout": 500,
        "retries": 3,
        "rtu": _base_device_modbus_properties_kwargs(kwargs),
        **kwargs,
    }
    return kwargs


def _serial_device_property_list_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    kwargs = {
        "template": "",
        "alias": "",
        "replace": {},
        "protocol": "ModbusRTU",
        "rtu": _device_rtu_properties_kwargs(kwargs),
        **kwargs,
    }
    return kwargs


def _tcp_device_obj_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    kwargs = {
        **_base_bacnet_obj_kwargs({}),
        "371": json.dumps(_tcp_device_property_list_kwargs(kwargs)),
        **kwargs,
    }
    return kwargs


def _modbus_tcp_device_obj_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    kwargs = {
        **_base_bacnet_obj_kwargs({}),
        "371": json.dumps(_modbus_tcp_device_property_list_kwargs(kwargs)),
        **kwargs,
    }
    return kwargs


def _serial_device_obj_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    kwargs = {
        **_base_bacnet_obj_kwargs(kwargs),
        "371": json.dumps(_serial_device_property_list_kwargs(kwargs)),
        **kwargs,
    }
    return kwargs


def _modbus_properties_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    kwargs = {
        "address": 11,
        "quantity": 2,
        "functionRead": "0x04",
        "dataType": "float",
        "dataLength": 32,
        "scale": 10,
        "functionWrite": "0x06",
        "wordOrder": "little",
        **kwargs,
    }
    return kwargs


def _bacnet_obj_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    kwargs = {
        **_base_bacnet_obj_kwargs(kwargs),
        "103": "no-fault-detected",
        "106": None,
        "111": [False, False, False, False],
        "85": 85.8585,
        "timestamp": "2011-11-11 11:11:11",
        **kwargs,
    }
    return kwargs


def _jsonrpc_set_point_params(kwargs: dict[str, Any]) -> dict[str, Any]:
    kwargs = {
        "device_id": "846",
        "object_type": "1",
        "object_id": "75",
        "property": "85",
        "priority": "8",
        "index": "-1",
        "tag": "9",
        "value": "22.22",
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

from pydantic import Field

from ..bacnet.obj_property_list import BaseBACnetObjPropertyList
from .modbus_properties import ModbusProperties


class ModbusPropertyList(BaseBACnetObjPropertyList):
    """Property list (371) for Modbus devices."""

    modbus: ModbusProperties = Field(...)

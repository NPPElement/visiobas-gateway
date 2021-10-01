from pydantic import Field

from ..bacnet.obj_property_list import BACnetObjPropertyList
from .modbus_properties import ModbusProperties


class ModbusPropertyList(BACnetObjPropertyList):
    """Property list (371) for Modbus devices."""

    modbus: ModbusProperties = Field(...)

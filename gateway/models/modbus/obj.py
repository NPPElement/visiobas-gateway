from typing import Union

from pydantic import Field, validator

from .obj_property_list import ModbusPropertyListWrapper
from ..bacnet.obj import BACnetObjModel
from ..bacnet.obj_property import ObjProperty


class ModbusObjModel(BACnetObjModel):
    property_list: Union[str, ModbusPropertyListWrapper] = Field(
        alias=ObjProperty.propertyList.id_str)

    @validator('property_list')
    def parse_property_list(cls, pl: str) -> ModbusPropertyListWrapper:
        return ModbusPropertyListWrapper.parse_raw(pl)

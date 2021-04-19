from typing import Union

from pydantic import Field, validator

from .obj_property_list import ModbusPropertyListWrap
from ..bacnet.obj import BACnetObjModel
from ..bacnet.obj_property import ObjProperty


class ModbusObjModel(BACnetObjModel):
    property_list: Union[str, ModbusPropertyListWrap] = Field(
        alias=ObjProperty.propertyList.id_str)

    @validator('property_list')
    def parse_property_list(cls, pl: str) -> ModbusPropertyListWrap:
        return ModbusPropertyListWrap.parse_raw(pl)

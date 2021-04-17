
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


# class ModbusObj(NamedTuple):
#     # type: ObjType
#     id: int
#     name: str
#     # upd_period: int
#     properties: VisioModbusProperties
#
#     @property
#     def topic(self):
#         return self.name.replace(':', '/').replace('.', '/')
#
#     @classmethod
#     def create_from_dict(cls, obj_type: ObjType, obj_props: dict):
#         # FIXME: make cast obj type from props (int)
#
#         obj_id = obj_props[str(ObjProperty.objectIdentifier.id)]
#         obj_name = obj_props[str(ObjProperty.objectName.id)]
#
#         prop_list = obj_props[str(ObjProperty.propertyList.id)]
#
#         vb_props = VisioModbusProperties.create_from_json(
#             property_list=prop_list)
#
#         return cls(type=obj_type,
#                    id=obj_id,
#                    name=obj_name,
#                    properties=vb_props
#                    )

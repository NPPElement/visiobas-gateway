from typing import NamedTuple

from gateway.models.bacnet import ObjType, ObjProperty
from .properties import VisioModbusProperties


class ModbusObj(NamedTuple):
    type: ObjType
    id: int
    name: str
    # upd_period: int

    properties: VisioModbusProperties

    @classmethod
    def create_from_dict(cls, obj_type: ObjType, obj_props: dict):
        # FIXME: make cast obj type from props (int)

        obj_id = obj_props[str(ObjProperty.objectIdentifier.id)]
        obj_name = obj_props[str(ObjProperty.objectName.id)]

        prop_list = obj_props[str(ObjProperty.propertyList.id)]

        vb_props = VisioModbusProperties.create_from_json(
            property_list=prop_list)

        return cls(type=obj_type,
                   id=obj_id,
                   name=obj_name,
                   properties=vb_props
                   )


if __name__ == '__main__':
    obj1 = ModbusObj(type=ObjType.BINARY_OUTPUT,
                     id=1,
                     name='',
                     properties=VisioModbusProperties(
                         address=1,
                         quantity=1,
                         func_read=3,
                         func_write=6,
                         scale=1,
                         data_type='INT',
                         data_length=16,
                         bit=None
                     ))

    obj2 = ModbusObj(type=ObjType.BINARY_OUTPUT,
                     id=1,
                     name='',
                     properties=VisioModbusProperties(
                         address=1,
                         quantity=1,
                         func_read=3,
                         func_write=6,
                         scale=1,
                         data_type='INT',
                         data_length=16,
                         bit=None
                     ))
    print(hash(obj1) == hash((ObjType.BINARY_OUTPUT, 1)))

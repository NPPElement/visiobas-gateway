from typing import NamedTuple

from .obj_property import ObjProperty
from .obj_type import ObjType


class BACnetObj(NamedTuple):
    type: ObjType
    id: int

    name: str
    resolution: float = None  # todo
    update_interval: int = None  # TODO: implement skip by update_interval

    @property
    def topic(self):
        return self.name.replace(':', '/').replace('.', '/')

    @classmethod
    def from_dict(cls, obj_type: ObjType, obj_props: dict):
        obj_id = obj_props[str(ObjProperty.objectIdentifier.id)]
        obj_name = obj_props[str(ObjProperty.objectName.id)]

        return cls(type=obj_type,
                   id=obj_id,
                   name=obj_name
                   )

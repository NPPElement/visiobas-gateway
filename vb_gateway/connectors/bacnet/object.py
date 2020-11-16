from typing import NamedTuple

from vb_gateway.connectors.bacnet.obj_type import ObjType


class BACnetObject(NamedTuple):
    type: ObjType
    id: int
    name: str

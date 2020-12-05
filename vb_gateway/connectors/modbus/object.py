from typing import NamedTuple

from vb_gateway.connectors.bacnet.obj_type import ObjType


class ModbusObject(NamedTuple):
    type: ObjType
    id: int
    name: str

    address: int
    quantity: int
    func_read: int
    scale: int

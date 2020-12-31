from typing import NamedTuple

from vb_gateway.connectors.bacnet.obj_type import ObjType


class VisioModbusProperties(NamedTuple):
    scale: int
    data_type: str
    data_length: int
    byte_order: str

    bit: int or None = None


class ModbusObject(NamedTuple):
    type: ObjType
    id: int
    name: str

    address: int
    quantity: int
    func_read: int

    properties: VisioModbusProperties

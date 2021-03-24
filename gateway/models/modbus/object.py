from typing import Union

from pydantic import BaseModel, Field, validator

from ..bacnet import ObjProperty, BACnetObjModel
from ..modbus import ModbusFunc


class ModbusPropertiesModel(BaseModel):
    address: int = Field(gt=0)
    quantity: int = Field(gt=0)
    func_read: ModbusFunc = Field(..., alias='functionRead')
    func_write: ModbusFunc = Field(default=ModbusFunc.WRITE_REGISTER, alias='functionWrite')

    # TODO: change to 'multiplier' \ change operation in scaled value
    scale: float = 1
    # for recalculate (A*X+B)
    # multiplier: float  # A # todo
    # corrective: float  # B# todo

    data_type: str = Field(..., alias='dataType')
    data_length: int = Field(default=16, gt=1, lt=64, alias='dataLength')
    # the number of bits in which the value is stored

    # byte_order: str # todo
    # word_order: str# todo

    # bitmask = int todo
    bit: Union[int, None] = None  # TODO: change to 'bitmask'

    # @validator('func_write')
    # def set_default_func_write(cls, v) -> int:
    #     return int((v or '0x06')[-2:])


class PropertyListModel(BaseModel):
    modbus: ModbusPropertiesModel

    @property
    def address(self) -> int:
        return self.modbus.address

    @property
    def func_read(self) -> ModbusFunc:
        return self.modbus.func_read

    @property
    def func_write(self) -> ModbusFunc:
        return self.modbus.func_write

    @property
    def quantity(self) -> int:
        return self.modbus.quantity


class ModbusObjModel(BACnetObjModel):
    property_list: str = Field(alias=ObjProperty.propertyList.id_str)

    @validator('property_list')
    def parse_property_list(cls, v):
        # JSON of property list is str
        return PropertyListModel.parse_raw(v)

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

from json import loads
from typing import Union

from pydantic import BaseModel, Field, validator

from .obj_property import ObjProperty
from .obj_type import ObjType


class ModbusPropertiesModel(BaseModel):
    address: int


class PropertyListModel(BaseModel):
    modbus: ModbusPropertiesModel


class BACnetObjModel(BaseModel):
    # for evident exception use code below + validation
    # # type: Union[int, str] = Field(..., alias=ObjProperty.objectType.id_str)

    type: ObjType = Field(..., alias=ObjProperty.objectType.id_str)
    id: int = Field(..., ge=0, alias=ObjProperty.objectIdentifier.id_str)
    name: str = Field(..., alias=ObjProperty.objectName.id_str)

    # property_list: str = Field(alias=ObjProperty.propertyList.id_str)

    # status_flags: Union[list[bool], None] = Field(alias=ObjProperty.statusFlags.id_str)
    # priority_array: Union[str, None] = Field(alias=ObjProperty.priorityArray.id_str)
    # reliability: Union[str, None] = Field(alias=ObjProperty.reliability.id_str)

    resolution: Union[float, int, None] = Field(alias=ObjProperty.resolution.id_str)
    upd_interval: Union[float, int, None] = Field(alias=ObjProperty.updateInterval.id_str)
    _last_value = None

    # @validator('type')
    # def cast_to_obj_type(cls, v):
    #     print(type(v), v)
    #     return ObjType(v)

    @validator('resolution')
    def set_default_resolution(cls, v):
        return v or .1

    # @validator('property_list')
    # def parse_property_list(cls, v):
    #     return PropertyListModel.parse_raw(v)

    @property
    def topic(self):
        return self.name.replace(':', '/').replace('.', '/')


# class BACnetObjectsDataModel(BaseModel):
#     success: bool = Field(default=...)
#     data: list[BACnetObjModel] = Field(default=...)
#
#     @validator('success')
#     def successful(cls, v):
#         if v:
#             return v
#         raise ValueError('Must be True')
#
#     @validator('')


# class BACnetObj(NamedTuple):
#     # type: ObjType
#     id: int
#
#     name: str
#     resolution: float = None  # todo
#     update_interval: int = None  # TODO: implement skip by update_interval
#
#     @property
#     def topic(self):
#         return self.name.replace(':', '/').replace('.', '/')
#
#     @classmethod
#     def from_dict(cls, obj_type: ObjType, obj_props: dict):
#         obj_id = obj_props[str(ObjProperty.objectIdentifier.id)]
#         obj_name = obj_props[str(ObjProperty.objectName.id)]
#
#         return cls(type=obj_type,
#                    id=obj_id,
#                    name=obj_name
#                    )


data_dict = {'103': 'no-fault-detected',
             '106': None,
             '111': [False, True, False, False],
             '113': None,
             '117': None,
             '118': None,
             '130': None,
             '133': True,
             '168': None,
             '17': None,
             '22': 0.1,
             '25': None,
             '28': 'Температура в помещении трансформатора 2.',
             '31': None,
             '35': [False, False, False],
             '351': None,
             '352': None,
             '353': None,
             '354': None,
             '355': None,
             '356': None,
             '357': None,
             '36': None,
             '371': '{"template":"","alias":"TEMP_TR2","replace":{},"modbus":{"address":1007,"quantity":2,"functionRead":"0x04","dataType":"FLOAT","dataLenght":32,"scale":10}}',
             '45': None,
             '52': None,
             '59': None,
             '65': None,
             '69': None,
             '72': None,
             '75': 496,
             '77': 'Site:Engineering/Electricity.TP_1002.Temperature.AI_703',
             '79': 'binary-input',
             '81': None,
             '846': 1673,
             '85': 0.0,
             'timestamp': '2021-02-04 05:47:23'}

obj = BACnetObjModel(**data_dict)
print(obj)

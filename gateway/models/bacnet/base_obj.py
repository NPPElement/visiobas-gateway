from pydantic import BaseModel, Field, Json

from .obj_property import ObjProperty
from .obj_type import ObjType


class BaseBACnetObjModel(BaseModel):
    # for evident exception use code below + validation
    # # type: Union[int, str] = Field(..., alias=ObjProperty.objectType.id_str)
    type: ObjType = Field(..., alias=ObjProperty.objectType.id_str)

    device_id: int = Field(..., gt=0, alias=ObjProperty.deviceId.id_str)
    id: int = Field(..., ge=0, alias=ObjProperty.objectIdentifier.id_str)

    # name: str = Field(..., alias=ObjProperty.objectName.id_str) deprecated

    property_list: Json = Field(alias=ObjProperty.propertyList.id_str)

    # todo add MQTT topic property

    # def __repr__(self) -> str:
    #     return str(self.__dict__)
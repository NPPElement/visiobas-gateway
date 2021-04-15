from pydantic import BaseModel, Field

from gateway.models import ObjProperty, ObjType


class BaseBACnetObjModel(BaseModel):
    # for evident exception use code below + validation
    # # type: Union[int, str] = Field(..., alias=ObjProperty.objectType.id_str)
    type: ObjType = Field(..., alias=ObjProperty.objectType.id_str)

    device_id: int = Field(..., gt=0, alias=ObjProperty.deviceId.id_str)

    id: int = Field(..., ge=0, alias=ObjProperty.objectIdentifier.id_str)
    name: str = Field(..., alias=ObjProperty.objectName.id_str)

    property_list: str = Field(alias=ObjProperty.propertyList.id_str)

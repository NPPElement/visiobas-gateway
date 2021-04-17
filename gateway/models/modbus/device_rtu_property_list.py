# from typing import Union
#
# from pydantic import BaseModel, Field, validator
#
#
# class DeviceRTUPropertyListModel(BaseModel):
#     port: str = Field(...)
#     baudrate: int = Field(..., gt=0, lt=115200)
#     stopbits: int = Field(default=1)
#     bytesize: int = Field(default=8)
#     timeout: float = Field(default=1)
#     parity: Union[None, str] = Field(default='None')
#
#     @validator('parity')
#     def process_parity(cls, parity: str) -> None:
#         if parity is 'None':
#             parity = None
#         return parity
#
#
# class DeviceRTUPropertyListWrapper(BaseModel):
#     rtu: DeviceRTUPropertyListModel = Field(...)
#
#

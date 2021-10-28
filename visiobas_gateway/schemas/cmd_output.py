from pydantic import BaseModel
from typing import Union


class CmdInfo(BaseModel):

    cmd: Union[str, bytes]
    description: str
    options: list[Union[str, bytes]]
    parameters: list[Union[str, bytes]]
    return_code: int
    stdout: bytes

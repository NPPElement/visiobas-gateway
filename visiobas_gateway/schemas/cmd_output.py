from typing import Union

from pydantic import BaseModel


class CmdInfo(BaseModel):
    """Contains information about executed command."""

    description: str
    cmd: Union[str, bytes]
    options: list[Union[str, bytes]]
    parameters: list[Union[str, bytes]]
    return_code: int
    stdout: bytes

import os
import sys
from typing import Union

from pydantic import BaseModel, Field

from ..cmd_output import CmdInfo
from ..serial_port import SerialPort
from visiobas_gateway import GATEWAY_VERSION
from ...utils.monitor import get_ram_usage, get_connected_serial_ports, is_virtualenv


class MonitorInfo(BaseModel):
    pid: int = Field(default_factory=os.getpid, ge=1, le=2**15)
    python_version: str = Field(default=sys.version)
    gateway_version: str = Field(default=GATEWAY_VERSION)
    virtualenv: bool = Field(default_factory=is_virtualenv)
    serial_ports: list[SerialPort] = Field(default_factory=get_connected_serial_ports)
    ram_usage: float = Field(default_factory=get_ram_usage)

    cmd_results: list[Union[CmdInfo, Exception]] = Field(...)


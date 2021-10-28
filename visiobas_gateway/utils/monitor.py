from __future__ import annotations

import asyncio
import os
import resource
import sys
from typing import Any

import serial.tools.list_ports  # type: ignore

from ..schemas import SerialPort
from ..schemas.cmd_output import CmdInfo
from ..schemas.gateway.monitor import MonitorInfo
from .log import get_file_logger

_LOG = get_file_logger(__name__)

_PID = os.getpid()

CommandData = tuple[str, list[str], list[str], str]

MONITOR_COMMANDS: tuple[CommandData, ...] = (
    # (cmd, options, parameters, description)
    ("uptime", ["-a"], [], "Uptime"),
    ("uname", ["-a"], [], "Kernel Information"),
    ("df", ["-h"], [], "Disk Usage"),
    ("free", ["-h"], [], "Memory"),
    ("dmesg", [], ["| tail -n 20"], "Diagnostic Messages"),
    ("ifconfig", ["-a"], [], "Network"),
    ("pstree", [f"-p {_PID}"], [], "Processes"),
    ("top", ["-bH", "-n 1", f"-p {_PID}"], [], "Processes"),
)


async def execute_cmd(
    cmd: str,
    *args: Any,
    options: list[str] = None,
    parameters: list[str] = None,
    cmd_description: str = None,
    **kwargs: Any,
) -> CmdInfo:
    options = options or []
    parameters = parameters or []
    
    process = await asyncio.create_subprocess_shell(
        " ".join((cmd, *options, *parameters)), *args, **kwargs
    )
    return_code = await process.wait()
    stdout = await process.stdout.read() if process.stdout else None

    cmd_info = CmdInfo(
        description=cmd_description,
        cmd=cmd,
        options=options,
        parameters=parameters,
        return_code=return_code,
        stdout=stdout,
    )
    _LOG.debug("Executed command", extra={"cmd_info": cmd_info})
    return cmd_info


def get_ram_usage() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / float(1000)


def get_connected_serial_ports() -> list[str]:
    return [port.device for port in serial.tools.list_ports.comports() if port.location]


def is_serial_port_connected(serial_port: SerialPort) -> bool:
    return serial_port in get_connected_serial_ports()


def is_virtualenv() -> bool:
    return bool(hasattr(sys, "real_prefix") or sys.base_prefix != sys.prefix)


async def get_cmd_results(cmds: tuple[CommandData, ...]) -> tuple[CmdInfo | Exception, ...]:
    cmd_tasks = [execute_cmd(*cmd_data) for cmd_data in cmds]
    return await asyncio.gather(*cmd_tasks)  # type: ignore


async def get_monitor_info(cmds: tuple[CommandData, ...]) -> MonitorInfo:
    cmd_results = await get_cmd_results(cmds=cmds)
    return MonitorInfo(cmd_results=cmd_results)

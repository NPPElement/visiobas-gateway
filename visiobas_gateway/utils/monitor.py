from __future__ import annotations

import asyncio
import os
import resource
import sys

import serial.tools.list_ports  # type: ignore

from ..schemas import SerialPort
from ..schemas.cmd_output import CmdInfo
from .log import get_file_logger
from ..schemas.gateway.monitor import MonitorInfo

_LOG = get_file_logger(__name__)

_PID = os.getpid()

MONITOR_COMMANDS = (
    # (CMD description, cmd, options, parameters)
    ('Uptime', 'uptime', ['-a'], []),
    ('Kernel Information', 'uname', ['-a'], []),
    ('Disk Usage', 'df', ['-h'], []),
    ('Memory', 'free', ['-h'], []),
    ('Diagnostic Messages', 'dmesg', [], ['| tail -n 20']),
    ('Network', 'ifconfig', ['-a'], []),
    ('Processes', 'pstree', [f'-p {_PID}'], []),
    ('Processes', 'top', ['-bH', '-n 1', f'-p {_PID}'], [])
)


async def execute_cmd(
        cmd: str | bytes,
        options: list[str | bytes] = None,
        parameters: list[str | bytes] = None,
        *args, **kwargs
) -> CmdInfo:
    options = options or []
    parameters = parameters or []
    process = await asyncio.create_subprocess_shell(
        " ".join((cmd, *options, *parameters)), *args, **kwargs
    )
    return_code = await process.wait()
    stdout = await process.stdout.read()

    cmd_info = CmdInfo(cmd=cmd, options=options, parameters=parameters, return_code=return_code, stdout=stdout)
    _LOG.debug('Executed command', extra={'cmd_info': cmd_info})
    return cmd_info


def get_ram_usage() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / float(1000)


def get_connected_serial_ports() -> list[str]:
    return [port.device for port in serial.tools.list_ports.comports() if port.location]


def is_serial_port_connected(serial_port: SerialPort) -> bool:
    return serial_port in get_connected_serial_ports()


def is_virtualenv() -> bool:
    return True if hasattr(sys, 'real_prefix') or sys.base_prefix != sys.prefix else False


async def get_cmd_results(
        cmds: tuple[str, str, list[str], list[str]]
) -> tuple[CmdInfo | Exception, ...]:
    cmd_tasks = [execute_cmd(*cmd_data) for cmd_data in MONITOR_COMMANDS]
    return await asyncio.gather(*cmd_tasks)


async def get_monitor_info(cmds: tuple[str, str, list[str], list[str]]) -> MonitorInfo:
    cmd_results = await get_cmd_results(cmds=cmds)
    return MonitorInfo(cmd_results=cmd_results)

from __future__ import annotations

import asyncio
import os
import sys
import resource

from ..schemas.cmd_output import CmdInfo
from .log import get_file_logger
from .network import get_connected_serial_ports

_LOG = get_file_logger(__name__)

_PID = pid = os.getpid()

MONITOR_CMDS = (
    # (Whats cmd doing, cmd, options, parameters)
    ('Uptime', 'uptime', ['-a'], []),
    ('Uname', 'uname', ['-a'], []),
    ('DF', 'df', ['-h'], []),
    ('Free', 'free', ['-h'], []),
    ('', 'dmesg', [], ['| tail -n 20']),
    ('', 'ifconfig', ['-a'], []),
    ('', 'pstree', [f'-p {_PID}'], []),
    ('', 'top', ['-bH', '-n 1', f'-p {_PID}'], [])

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
    stdout = await process.stdout.read().

    cmd_info = CmdInfo(cmd=cmd, options=options, parameters=parameters, return_code=return_code, stdout=stdout)
    _LOG.debug('Executed command', extra={'cmd_info': cmd_info})
    return cmd_info


class Monitor:
    @staticmethod
    async def get_info():
        python_version = sys.version
        virtualenv = True if hasattr(sys, 'real_prefix') or sys.base_prefix != sys.prefix else False

        uptime = await execute_cmd(cmd='uptime', options=['-a'])
        uname = await execute_cmd(cmd='uname', options=['-a'])
        serial_ports = get_connected_serial_ports()

        ram_use = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / float(1000)
        ...
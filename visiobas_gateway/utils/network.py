from __future__ import annotations

import asyncio
import platform
from functools import lru_cache
from ipaddress import IPv4Address, IPv4Interface

from .log import get_file_logger

try:
    import netifaces  # type: ignore

    _NETIFACES_ENABLE = True
except ImportError:
    _NETIFACES_ENABLE = False

_LOG = get_file_logger(__name__)


@lru_cache(maxsize=10)
def get_subnet_interface(ip: IPv4Address) -> IPv4Interface | None:
    """
    Args:
        ip: Ip address in subnet.
    Returns:
        Interface in same subnet as `ip` which can be used to interact.
            None if no one exists.
    Raises:
        NotImplementedError: if `netifaces` not installed.
    """
    if not _NETIFACES_ENABLE:
        raise NotImplementedError(
            "`netifaces` must be installed to find available network interface"
        )
        # return _get_ip_address()
    if not isinstance(ip, IPv4Address):
        raise ValueError("Instance of `IPv4Address` expected")

    interfaces = netifaces.interfaces()
    _LOG.debug("Available interfaces", extra={"interfaces": interfaces})

    for nic in interfaces:
        addresses = netifaces.ifaddresses(nic)
        try:
            for address in addresses[netifaces.AF_INET]:
                interface = IPv4Interface(
                    address="/".join((address["addr"], address["netmask"]))
                )
                network = interface.network

                if ip in network:
                    _LOG.debug(
                        "Target IP is available via interface",
                        extra={"target_ip": ip, "interface": interface, "nic": nic},
                    )
                    return interface
                _LOG.debug(
                    "Target IP is not available via interface",
                    extra={"target_ip": ip, "interface": interface, "nic": nic},
                )
        except KeyError:
            pass
    return None


async def ping(host: str, attempts: int) -> bool:
    """
    Adopted from <https://stackoverflow.com/a/67745987>

    Args:
        host: Host to ping.
        attempts: Attempts quantity.

    Returns: Ping is successful.
    """
    current_os = platform.system().lower()
    parameter = "n" if current_os == "windows" else "c"
    ping_process = await asyncio.create_subprocess_shell(
        f"ping -{parameter} {attempts} {host}"
    )
    await ping_process.wait()
    return ping_process.returncode == 0


#
# def tty_exists(tty: str) -> bool:
#     pass


# def _get_ip_address() -> IPv4Interface:
#     """Attempt an internet connection and use the network adapter
#     connected to the internet.
#
#        Adopted from BAC0
#
#        Returns:
#            IP Address as String
#        Raises:
#            ConnectionError: If no addresses connected to internet.
#     """
#     s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     try:
#         s.connect(("google.com", 0))
#         ip_address = s.getsockname()[0]
#         s.close()
#     except socket.error as exc:
#         raise ConnectionError(
#             "Impossible to retrieve IP, please provide one manually or install "
#             "`netifaces`"
#         ) from exc
#     return IPv4Interface(ip_address)

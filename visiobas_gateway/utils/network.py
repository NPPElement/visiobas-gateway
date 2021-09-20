from ipaddress import IPv4Address, IPv4Interface
from typing import Optional

try:
    import netifaces  # type: ignore

    _NETIFACES_ENABLE = True
except ImportError:
    _NETIFACES_ENABLE = False


def get_subnet_interface(ip: IPv4Address) -> Optional[IPv4Interface]:
    """
    Args:
        ip: Ip address in subnet.
    Returns:
        Interface in same subnet as `ip` which can be used to interact.
            None if no one exists.
    Raises:
        NotImplementedError: if `netifaces` not installed
    """
    if not _NETIFACES_ENABLE:
        return None

    if not isinstance(ip, IPv4Address):
        raise ValueError("Instance of `IPv4Address` expected")

    interfaces = netifaces.interfaces()
    for nic in interfaces:
        addresses = netifaces.ifaddresses(nic)
        try:
            for address in addresses[netifaces.AF_INET]:
                interface = IPv4Interface(
                    address="/".join((address["addr"], address["netmask"]))
                )
                network = interface.network

                if ip in network:
                    return interface
        except KeyError:
            pass
    return None

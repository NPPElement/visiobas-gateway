from ipaddress import IPv4Address, IPv4Interface
from typing import Optional


def get_subnet_interface(ip: IPv4Address) -> Optional[IPv4Interface]:
    """
    Args:
        ip: Ip address in subnet.
    Returns:
        Interface in same subnet as `ip` which can be used to interact.
            None if no one exists.
    """
    if not isinstance(ip, IPv4Address):
        raise ValueError("Instance of `IPv4Address` expected")
    try:
        import netifaces  # type: ignore

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

    except ImportError as e:
        raise e

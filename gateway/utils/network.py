from typing import Optional

from ipaddress import IPv4Address, IPv4Interface


def get_subnet_interface(ip: IPv4Address) -> Optional[IPv4Interface]:
    """
    Args:
        ip:

    Returns:
        Interface which can be used to interact with `ip`, None if no one exists.
    """
    if not isinstance(ip, IPv4Address):
        raise ValueError('Instance of `IPv4Address` expected')
    try:
        import netifaces

        interfaces = netifaces.interfaces()
        for nic in interfaces:
            addresses = netifaces.ifaddresses(nic)
            try:
                for address in addresses[netifaces.AF_INET]:
                    interface = IPv4Interface(
                        address='/'.join((address["addr"], address["netmask"]))
                    )
                    network = interface.network

                    if ip in network:
                        return interface
            except KeyError:
                pass
        return None

    except ImportError:
        raise NotImplementedError

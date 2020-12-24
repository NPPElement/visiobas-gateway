from ipaddress import IPv4Address
from pathlib import Path

from vb_gateway.connectors.bacnet.obj_property import ObjProperty


def get_fault_obj_properties(reliability: int or str,
                             pv='null',
                             sf: list = None) -> dict:
    """ Returns properties for unknown objects
    """
    if sf is None:
        sf = [0, 1, 0, 0]
    return {
        ObjProperty.presentValue: pv,
        ObjProperty.statusFlags: sf,
        ObjProperty.reliability: reliability
        #  todo: make reliability class as Enum
    }


def read_address_cache(address_cache_path: Path) -> dict[int, str]:
    """ Updates address_cache file

        Parse text file format of address_cache.
        Add information about devices

        Example of address_cache format:

        ;Device   MAC (hex)            SNET  SADR (hex)           APDU
        ;-------- -------------------- ----- -------------------- ----
          200     0A:15:50:0C:BA:C0    0     00                   480
          300     0A:15:50:0D:BA:C0    0     00                   480
          400     0A:15:50:0E:BA:C0    0     00                   480
          500     0A:15:50:0F:BA:C0    0     00                   480
          600     0A:15:50:10:BA:C0    0     00                   480
        ;
        ; Total Devices: 5
    """
    try:
        text = address_cache_path.read_text(encoding='utf-8')
    except FileNotFoundError as e:
        raise e

    address_cache = {}

    for line in text.split('\n'):
        trimmed = line.strip()
        if not trimmed.startswith(';') and trimmed:
            try:
                device_id, mac, _, _, apdu = trimmed.split()
                # In mac we have ip-address host:port in hex
                device_id = int(device_id)
                addr1, addr2, addr3, addr4, port1, port2 = mac.rsplit(':', maxsplit=5)
                addr = IPv4Address('.'.join((
                    str(int(addr1, base=16)),
                    str(int(addr2, base=16)),
                    str(int(addr3, base=16)),
                    str(int(addr4, base=16)))))
                port = int(port1 + port2, base=16)
                address_cache[device_id] = str(addr) + str(port)
            except ValueError:
                continue
    return address_cache

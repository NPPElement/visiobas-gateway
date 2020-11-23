from pathlib import Path

from vb_gateway.connectors.bacnet.obj_property import ObjProperty
from vb_gateway.connectors.bacnet.status_flags import StatusFlags


def get_fault_obj_properties(reliability: int or str,
                             pv='null',
                             sf: StatusFlags = StatusFlags([0, 1, 0, 0])) -> dict:
    """ Returns properties for unknown objects
    """
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
            except ValueError:
                continue
            device_id = int(device_id)
            # In mac we have ip-address host:port in hex
            mac = mac.split(':')
            address = '{}.{}.{}.{}:{}'.format(int(mac[0], base=16),
                                              int(mac[1], base=16),
                                              int(mac[2], base=16),
                                              int(mac[3], base=16),
                                              int(''.join((mac[4], mac[5])), base=16))
            address_cache[device_id] = address
    return address_cache

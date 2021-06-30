from functools import lru_cache
from ipaddress import IPv4Address
from logging import getLogger
from pathlib import Path

from pymodbus.payload import BinaryPayloadDecoder

# FIXME
from gateway.models import ObjProperty, StatusFlag

_log = getLogger(__name__)


@lru_cache(maxsize=2)
def read_address_cache(path: Path) -> dict[int, str]:
    """Reads address_cache file.
    Caches the read result. Therefore, the cache must be cleared on update.

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

    :return: Example:
        200: '10.21.80.200:47808'
    """
    try:
        address_cache = {}

        text = path.read_text(encoding='utf-8')
        for line in text.split('\n'):
            trimmed = line.strip()
            if not trimmed.startswith(';') and trimmed:
                try:
                    device_id, mac, _, _, apdu = trimmed.split(maxsplit=4)
                    # In mac we have ip-address host:port in hex
                    device_id = int(device_id)
                    addr1, addr2, addr3, addr4, port1, port2 = mac.rsplit(':',
                                                                          maxsplit=5)
                    addr = IPv4Address('.'.join((
                        str(int(addr1, base=16)),
                        str(int(addr2, base=16)),
                        str(int(addr3, base=16)),
                        str(int(addr4, base=16)))))
                    port = int(port1 + port2, base=16)
                    address_cache[device_id] = ':'.join((str(addr), str(port)))
                except ValueError:
                    continue
        return address_cache

    except Exception as e:
        _log.critical(f'Read address_cache error: {e}')


def get_fault_obj_properties(reliability: int or str,
                             pv='null',
                             sf: int = StatusFlag.FAULT.value) -> dict:
    """ Returns properties for unknown objects
    """
    return {ObjProperty.presentValue: pv,
            ObjProperty.statusFlags: sf,
            ObjProperty.reliability: reliability
            #  todo: make reliability class as Enum
            }


def cast_to_bit(register: list[int], bit: int) -> int:
    """ Extract a bit from 1 register """
    # TODO: implement several bits

    if 0 >= bit >= 15:
        raise ValueError("Parameter 'bit' must be 0 <= bit <= 15")

    decoder = BinaryPayloadDecoder.fromRegisters(registers=register)
    first = decoder.decode_bits()
    second = decoder.decode_bits()
    bits = [*second, *first]
    return int(bits[bit])


def cast_2_registers(registers: list[int],
                     data_len: int,
                     byteorder: str, wordorder: str,
                     type_name: str) -> int or float:
    """ Cast two registers to selected type"""
    decoder = BinaryPayloadDecoder.fromRegisters(
        registers=registers,
        byteorder=byteorder,
        wordorder=wordorder
    )
    decode_func = {16: {'INT': decoder.decode_16bit_int,
                        'UINT': decoder.decode_16bit_uint,
                        'FLOAT': decoder.decode_16bit_float,
                        },
                   32: {'INT': decoder.decode_32bit_int,
                        'UINT': decoder.decode_32bit_uint,
                        'FLOAT': decoder.decode_32bit_float,
                        },
                   }
    # TODO: UNFINISHED
    try:
        return decode_func[data_len][type_name]()
    except KeyError:
        raise ValueError(f'Behavior for <{type_name}> not implemented')

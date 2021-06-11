import asyncio
from typing import Collection

# todo: process optional imports
from pymodbus.exceptions import ModbusException

from ..models import StatusFlags, StatusFlag, BACnetObj
from ..utils import get_file_logger

_LOG = get_file_logger(name=__name__)


class BACnetVerifier:
    def __init__(self, override_threshold: int = 8):
        self.override_threshold = override_threshold

    def __repr__(self) -> str:
        return self.__class__.__name__

    def verify_objects(self, objs: Collection[BACnetObj]):
        [self.verify(obj=obj) for obj in objs]

    def verify(self, obj: BACnetObj) -> None:
        if obj.exception:
            self.process_exception(obj=obj)
        else:
            self.verify_sf(obj=obj)
            self.verify_pv(obj=obj)

            if obj.pa is not None:
                self.verify_pa(obj=obj)

    @staticmethod
    def process_exception(obj: BACnetObj) -> None:
        obj.set_pv(value='null')
        obj.sf.enable(flag=StatusFlag.FAULT)

        if isinstance(obj.exception, (asyncio.TimeoutError, asyncio.CancelledError)):
            obj.reliability = 'timeout'
        elif isinstance(obj.exception, ModbusException):
            obj.reliability = str(obj.exception).replace(' ', '-')
        elif isinstance(obj.exception, (TypeError, ValueError)):
            obj.reliability = 'decode-error'
        else:
            RELIABILITY_LEN_LIMIT = 50
            str_exc = str(obj.exception)[-RELIABILITY_LEN_LIMIT:].strip().replace(' ', '-').replace(',', '-').replace(':', '-').replace('.', '-')
            obj.reliability = str_exc

        obj.exception = None

    @staticmethod
    def verify_sf(obj: BACnetObj) -> None:
        obj.sf = StatusFlags(flags=obj.sf)

    @staticmethod
    def verify_pv(obj: BACnetObj) -> None:
        if obj.pv in {True, 'active'}:
            obj.set_pv(value=1)
        elif obj.pv in {False, 'inactive'}:
            obj.set_pv(value=0)

        elif obj.pv in {'null', None}:
            obj.set_pv(value='null')
            obj.sf.enable(flag=StatusFlag.FAULT)
            # obj.reliability todo is reliability set?
        elif obj.pv == float('inf'):
            obj.set_pv(value='null')
            obj.sf.enable(flag=StatusFlag.FAULT)
            obj.reliability = 2
        elif obj.pv == float('-inf'):
            obj.set_pv(value='null')
            obj.sf.enable(flag=StatusFlag.FAULT)
            obj.reliability = 3
        elif isinstance(obj.pv, str) and not obj.pv.strip():
            obj.set_pv(value='null')
            obj.sf.enable(flag=StatusFlag.FAULT)
            obj.reliability = 'empty'

        if isinstance(obj.pv, float) and obj.pv.is_integer():
            obj.set_pv(value=int(obj.pv))  # FIXME: update time!

    def verify_pa(self, obj: BACnetObj) -> None:
        """Sets OVERRIDE status flag if priority array contains override priority."""

        # todo: move priorities into Enum
        # MANUAL_LIFE_SAFETY = 9 - 1
        # AUTOMATIC_LIFE_SAFETY = 10 - 1
        # OVERRIDE_PRIORITIES = {MANUAL_LIFE_SAFETY,
        #                        AUTOMATIC_LIFE_SAFETY, }
        for i in range(len(obj.pa)):
            if obj.pa[i] is not None and i >= self.override_threshold:
                obj.sf.enable(flag=StatusFlag.OVERRIDEN)

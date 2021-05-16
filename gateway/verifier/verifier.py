from logging import getLogger
from typing import Collection

from ..models import StatusFlags, StatusFlag, BACnetObjModel

_LOG = getLogger(__name__)


class BACnetVerifier:
    def __init__(self, override_threshold: int = 8):
        self.override_threshold = override_threshold

    def __repr__(self) -> str:
        return self.__class__.__name__

    def verify_objects(self, objs: Collection[BACnetObjModel]):
        [self.verify(obj=obj) for obj in objs]

    def verify(self, obj: BACnetObjModel) -> None:
        self.verify_sf(obj=obj)
        self.verify_pv(obj=obj)

        if obj.pa is not None:
            self.verify_pa(obj=obj)

    @staticmethod
    def verify_sf(obj: BACnetObjModel) -> None:
        obj.sf = StatusFlags(flags=obj.sf)

    @staticmethod
    def verify_pv(obj: BACnetObjModel) -> None:
        if obj.pv == 'active':
            obj.pv = 1
        elif obj.pv == 'inactive':
            obj.pv = 0

        elif obj.pv is None:
            obj.pv = 'null'
            obj.sf.enable(flag=StatusFlag.FAULT)
            # obj.reliability todo is reliability set?
        elif obj.pv == float('inf'):
            obj.pv = 'null'
            obj.sf.enable(flag=StatusFlag.FAULT)
            obj.reliability = 2
        elif obj.pv == float('-inf'):
            obj.pv = 'null'
            obj.sf.enable(flag=StatusFlag.FAULT)
            obj.reliability = 3

        elif isinstance(obj.pv, str) and not obj.pv.strip():
            obj.pv = 'null'
            obj.sf.enable(flag=StatusFlag.FAULT)
            obj.reliability = 'empty'

    def verify_pa(self, obj: BACnetObjModel) -> None:
        """Sets OVERRIDE status flag if priority array contains override priority."""

        # todo: move priorities into Enum
        # MANUAL_LIFE_SAFETY = 9 - 1
        # AUTOMATIC_LIFE_SAFETY = 10 - 1
        # OVERRIDE_PRIORITIES = {MANUAL_LIFE_SAFETY,
        #                        AUTOMATIC_LIFE_SAFETY, }
        for i in range(len(obj.pa)):
            if obj.pa[i] is not None and i >= self.override_threshold:
                obj.sf.enable(flag=StatusFlag.OVERRIDEN)
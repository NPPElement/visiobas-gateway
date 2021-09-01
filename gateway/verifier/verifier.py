from typing import Collection, Iterator, Union

from ..models import BACnetObj, StatusFlag, StatusFlags
from ..utils import get_file_logger

_LOG = get_file_logger(name=__name__)


class BACnetVerifier:
    """Represent data process workflow."""

    def __init__(self, override_threshold: int = 8):
        self.override_threshold = override_threshold

    def __repr__(self) -> str:
        return self.__class__.__name__

    def verify_objects(self, objs: Collection[BACnetObj]) -> Iterator[BACnetObj]:
        return (self.verify(obj=obj) for obj in objs)

    def verify(self, obj: BACnetObj) -> BACnetObj:
        if isinstance(obj.present_value, Exception):
            obj = self.process_exception(obj=obj, exc=obj.present_value)
            return obj
        obj.unreachable_in_row = 0
        obj.reliability = ""

        previous_value = obj.verified_present_value
        obj = self.verify_present_value(obj=obj, value=obj.present_value)
        if previous_value != obj.verified_present_value:
            obj.changed = obj.updated

        obj = self.verify_status_flags(
            obj=obj, status_flags=StatusFlags(flags=obj.status_flags)
        )
        if obj.priority_array:
            obj = self.verify_pa(obj=obj)
        return obj

    @staticmethod
    def process_exception(obj: BACnetObj, exc: Exception) -> BACnetObj:
        import asyncio

        try:
            from BAC0.core.io.IOExceptions import UnknownObjectError  # type: ignore
        except ImportError as import_exc:
            raise NotImplementedError from import_exc

        obj.unreachable_in_row += 1
        obj.present_value = "null"

        if isinstance(exc, (asyncio.TimeoutError, asyncio.CancelledError)):
            obj.reliability = "timeout"
            return obj
        if isinstance(exc, UnknownObjectError):
            obj.existing = False
            obj.reliability = "non-existent-object"
            return obj
        if isinstance(exc, (TypeError, ValueError)):
            obj.reliability = "decode-error"
        obj.reliability = (
            exc.__class__.__name__.strip()
            .replace(" ", "-")
            .replace(",", "-")
            .replace(":", "-")
            .replace(".", "-")
            .replace("/", "-")
            .replace("[", "")
            .replace("]", "")
        )
        return obj

    @staticmethod
    def verify_status_flags(obj: BACnetObj, status_flags: StatusFlags) -> BACnetObj:
        if obj.verified_present_value == "null":
            status_flags.enable(flag=StatusFlag.FAULT)

        if status_flags == 0:
            obj.reliability = ""

        obj.status_flags = status_flags
        return obj

    @staticmethod
    def verify_present_value(
        obj: BACnetObj, value: Union[str, int, float, bool]
    ) -> BACnetObj:
        # FIXME: detect changes
        if value in {True, "active"}:
            obj.verified_present_value = 1
            return obj
        if value in {False, "inactive"}:
            obj.verified_present_value = 0
            return obj
        if isinstance(value, str):
            if value == "null" or not value.strip():
                obj.verified_present_value = "null"
            obj.verified_present_value = value
            return obj
        if isinstance(value, (int, float)):
            if obj.type.is_analog:
                obj.verified_present_value = _round(value=value, resolution=obj.resolution)
            if value == float("inf"):
                obj.verified_present_value = "null"
                obj.reliability = 2
            elif value == float("-inf"):
                obj.verified_present_value = "null"
                obj.reliability = 3
            if isinstance(value, float) and value.is_integer():
                obj.verified_present_value = int(value)
            return obj

        obj.reliability = "unexpected-value-type"
        obj.verified_present_value = "null"
        return obj

    def verify_pa(self, obj: BACnetObj) -> BACnetObj:
        """Sets OVERRIDE status flag if priority array contains override priority."""

        # todo: move priorities into Enum
        # MANUAL_LIFE_SAFETY = 9 - 1
        # AUTOMATIC_LIFE_SAFETY = 10 - 1
        # OVERRIDE_PRIORITIES = {MANUAL_LIFE_SAFETY,
        #                        AUTOMATIC_LIFE_SAFETY, }
        for i, priority in enumerate(obj.priority_array):
            if priority is not None and i >= self.override_threshold:
                obj.status_flags.enable(flag=StatusFlag.OVERRIDEN)
        return obj


def _round(value: Union[float, int], resolution: Union[int, float]) -> float:
    rounded = round(value / resolution) * resolution

    if isinstance(resolution, int):
        return rounded
    if isinstance(resolution, float):
        _, fractional_part = str(resolution).split(".", maxsplit=1)
        digits = len(fractional_part)
        return round(rounded, ndigits=digits)
    raise ValueError("Expected int | float")

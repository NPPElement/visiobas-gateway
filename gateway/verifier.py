from typing import Collection, Iterator, Optional, Union

from .models.bacnet import ANALOG_TYPES, BACnetObj, StatusFlag, StatusFlags
from .models.settings import LogSettings
from .utils import get_file_logger, round_with_resolution

_LOG = get_file_logger(name=__name__, settings=LogSettings())


class BACnetVerifier:
    """Represent data process workflow."""

    def __init__(self, override_threshold: int = 8):
        self.override_threshold = override_threshold

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

        if not isinstance(exc, Exception):
            raise ValueError("Exception expected")

        obj.status_flags.enable(StatusFlag.FAULT)
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
            return obj
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
        if status_flags.flags == 0b0000:
            obj.reliability = ""

        obj.status_flags = status_flags
        return obj

    @staticmethod
    def verify_present_value(
        obj: BACnetObj, value: Optional[Union[str, int, float, bool]]
    ) -> BACnetObj:
        # pylint: disable=too-many-return-statements
        # FIXME: detect changes
        if value is None:
            obj.verified_present_value = "null"
            return obj

        if isinstance(value, (str, bool)):
            if value in {True, "active"}:
                obj.verified_present_value = 1
                return obj
            if value in {False, "inactive"}:
                obj.verified_present_value = 0
                return obj
            # `bool` can be only True | False. It checked above
            if value == "null" or not value.strip():  # type: ignore
                obj.verified_present_value = "null"
            else:
                obj.verified_present_value = value
            return obj
        if isinstance(value, (int, float)):
            if value == float("inf"):
                obj.verified_present_value = "null"
                obj.reliability = 2
                return obj
            if value == float("-inf"):
                obj.verified_present_value = "null"
                obj.reliability = 3
                return obj
            if obj.type in ANALOG_TYPES:
                obj.verified_present_value = round_with_resolution(
                    value=value, resolution=obj.resolution
                )
            if isinstance(value, float) and value.is_integer():
                obj.verified_present_value = int(value)
            return obj

        obj.reliability = "invalid-value-type"
        obj.verified_present_value = "null"
        return obj

    def verify_pa(self, obj: BACnetObj) -> BACnetObj:
        """Sets OVERRIDE status flag if priority array contains override priority."""

        # todo: move priorities into Enum
        # MANUAL_LIFE_SAFETY = 9 - 1
        # AUTOMATIC_LIFE_SAFETY = 10 - 1
        # OVERRIDE_PRIORITIES = {MANUAL_LIFE_SAFETY,
        #                        AUTOMATIC_LIFE_SAFETY, }
        if obj.priority_array:
            for i, priority in enumerate(obj.priority_array):
                if priority is not None and i >= self.override_threshold:
                    obj.status_flags.enable(flag=StatusFlag.OVERRIDEN)
        return obj

from typing import Collection, Optional, Union

from .schemas import (
    ANALOG_TYPES,
    BINARY_TYPES,
    MULTI_STATE_TYPES,
    BACnetObj,
    Priority,
    Reliability,
    StatusFlag,
    StatusFlags,
)
from .utils import get_file_logger, log_exceptions, round_with_resolution

_LOG = get_file_logger(name=__name__)


class BACnetVerifier:
    """Represent data process workflow."""

    def __init__(self, override_threshold: Priority = Priority.MANUAL_OPERATOR):
        self.override_threshold = override_threshold

    def verify_objects(self, objs: Collection[BACnetObj]) -> list[BACnetObj]:
        return [self.verify(obj=obj) for obj in objs]

    @log_exceptions(logger=_LOG)
    def verify(self, obj: BACnetObj) -> BACnetObj:
        if isinstance(obj.present_value, Exception):
            obj = self.process_exception(obj=obj, exc=obj.present_value)
            return obj
        obj.unreachable_in_row = 0
        obj.reliability = Reliability.NO_FAULT_DETECTED

        previous_value = obj.verified_present_value
        obj = self.verify_present_value(obj=obj, value=obj.present_value)
        if previous_value != obj.verified_present_value:
            obj.changed = obj.updated
        obj.present_value = obj.verified_present_value

        obj = self.type_check(obj=obj)

        obj = self.verify_status_flags(obj=obj, status_flags=obj.status_flags)
        if obj.priority_array:
            obj = self.verify_priority_array(obj=obj, priority_array=obj.priority_array)
        return obj

    @staticmethod
    def process_exception(obj: BACnetObj, exc: Exception) -> BACnetObj:
        import asyncio

        try:
            from BAC0.core.io.IOExceptions import (  # type: ignore
                NoResponseFromController,
                UnknownObjectError,
            )
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
        if isinstance(exc, (UnknownObjectError, NoResponseFromController)):
            obj.existing = False
            obj.reliability = Reliability.NO_SENSOR
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
            obj.reliability = Reliability.NO_FAULT_DETECTED

        obj.status_flags = status_flags
        return obj

    @staticmethod
    def type_check(obj: BACnetObj) -> BACnetObj:
        if obj.object_type in BINARY_TYPES:
            if obj.present_value not in {1, 0}:
                obj.reliability = "bad_binary_value"
        if obj.object_type in MULTI_STATE_TYPES:
            if not 0 <= obj.present_value <= 10:
                obj.reliability = "bad_multistate_value"

        return obj

    @staticmethod
    def verify_present_value(
        obj: BACnetObj, value: Optional[Union[str, int, float, bool]]
    ) -> BACnetObj:
        # pylint: disable=too-many-return-statements
        if not value.__hash__ or value in {None, "null"}:
            obj.verified_present_value = "null"
            obj.reliability = Reliability.NO_OUTPUT
            return obj
        if value in {True, "active"}:
            obj.verified_present_value = 1
            return obj
        if value in {False, "inactive"}:
            obj.verified_present_value = 0
            return obj
        if value == float("inf"):
            obj.verified_present_value = "null"
            obj.reliability = Reliability.OVER_RANGE
            return obj
        if value == float("-inf"):
            obj.verified_present_value = "null"
            obj.reliability = Reliability.UNDER_RANGE
            return obj

        if isinstance(value, str):
            try:
                value = float(value)
            except ValueError:
                # Other `str` values unexpected here
                obj.reliability = "unexpected-value"
                obj.verified_present_value = "null"
                return obj

        if isinstance(value, (int, float)):
            if obj.object_type in ANALOG_TYPES:
                value = round_with_resolution(value=value, resolution=obj.resolution)
            if isinstance(value, float) and value.is_integer():
                value = int(value)
            obj.verified_present_value = value
            return obj

        # Unexpected types
        obj.reliability = "unexpected-type"
        obj.verified_present_value = "null"
        return obj

    def verify_priority_array(
        self, obj: BACnetObj, priority_array: list[Optional[float]]
    ) -> BACnetObj:
        """Sets OVERRIDE status flag if priority array contains override priority."""
        for i, priority in enumerate(priority_array):
            if priority is None:
                continue
            if i >= int(self.override_threshold):
                obj.status_flags.enable(flag=StatusFlag.OVERRIDEN)

        obj.priority_array = priority_array
        return obj

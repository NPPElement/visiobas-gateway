from __future__ import annotations

from typing import Optional

from bacpypes.basetypes import PriorityArray  # type: ignore

from ..schemas import BACnetObj
from ..schemas.bacnet.obj_type import BINARY_TYPES
from ..utils import get_file_logger

_LOG = get_file_logger(name=__name__)


class BACnetCoderMixin:
    """Mixin for encode/decode interact with `bacpypes`."""

    @staticmethod
    def _is_binary_obj(obj: BACnetObj) -> bool:
        return obj.object_type in BINARY_TYPES

    @staticmethod
    def _encode_binary_present_value(value: int | float) -> str:
        if value:
            return "active"
        return "inactive"

    # def _decode_response(self, resp: Any, prop: ObjProperty) -> Any:
    #
    #     if prop is ObjProperty.PRIORITY_ARRAY:
    #         resp = self._decode_priority_array(priority_array=resp)
    #         return resp

    @staticmethod
    def _decode_priority_array(priority_array: PriorityArray) -> list[Optional[float]]:
        """Converts `bacpypes.PriorityArray` to list."""
        priority_array = [
            v[0] if k[0] != "null" else None
            for k, v in [
                zip(*priority_array.value[i].dict_contents().items())
                for i in range(1, priority_array.value[0] + 1)
            ]
        ]
        return priority_array

from __future__ import annotations

from typing import Iterable, Literal

from bacpypes.basetypes import PriorityArray  # type: ignore

from ...schemas import BACnetObj
from ...schemas.bacnet.obj_type import BINARY_TYPES
from ...utils import camel_case, get_file_logger

_LOG = get_file_logger(name=__name__)


class BACnetCoderMixin:
    """Mixin for encode/decode interact with `bacpypes`."""

    @staticmethod
    def _is_binary_obj(obj: BACnetObj) -> bool:
        return obj.object_type in BINARY_TYPES

    @staticmethod
    def _get_object_rpm_dict(obj: BACnetObj) -> dict[str, list]:
        """Returns object as dict for composing Read Property Multiple request."""
        _object_key = ":".join((camel_case(obj.object_type.name), str(obj.object_id)))
        return {_object_key: [camel_case(prop.name) for prop in obj.polling_properties]}

    @staticmethod
    def _get_objects_rpm_dict(objs: Iterable[BACnetObj]) -> dict[str, list]:
        objects_dict = {}
        for obj in objs:
            objects_dict.update(BACnetCoderMixin._get_object_rpm_dict(obj=obj))
        return objects_dict

    @staticmethod
    def _encode_binary_present_value(value: int | float) -> Literal["active", "inactive"]:
        return "active" if value else "inactive"

    # def _decode_response(self, resp: Any, prop: ObjProperty) -> Any:
    #
    #     if prop is ObjProperty.PRIORITY_ARRAY:
    #         resp = self._decode_priority_array(priority_array=resp)
    #         return resp

    @staticmethod
    def _decode_priority_array(priority_array: PriorityArray) -> list[float | None]:
        """Converts `bacpypes.PriorityArray` to list."""
        priority_array = [
            v[0] if k[0] != "null" else None
            for k, v in [
                zip(*priority_array.value[i].dict_contents().items())
                for i in range(1, priority_array.value[0] + 1)
            ]
        ]
        return priority_array

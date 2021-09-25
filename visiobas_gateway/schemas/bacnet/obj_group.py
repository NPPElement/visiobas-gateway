from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .obj import BACnetObj
else:
    BACnetObj = "BACnetObj"


@dataclass
class ObjectGroup:

    """todo replace to dict"""

    period: float

    # Unique object - tuple[object_id, object_type_id]
    objects: dict[tuple[int, int], BACnetObj]


def group_by_period(objs: list[BACnetObj]) -> dict[float, ObjectGroup]:
    """Groups objects by poll period and insert them into device for polling."""
    groups: dict[float, ObjectGroup] = {}

    for obj in objs:
        poll_period = obj.property_list.poll_period
        try:
            groups[poll_period].objects[(obj.id, obj.type.type_id)] = obj
        except KeyError:
            groups[poll_period] = ObjectGroup(
                period=poll_period, objects={(obj.id, obj.type.type_id): obj}
            )
    return groups

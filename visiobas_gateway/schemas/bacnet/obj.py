from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, Union

from pydantic import Field, validator

from ...utils import snake_case
from .base_obj import BaseBACnetObj
from .obj_property import ObjProperty
from .obj_property_list import BaseBACnetObjPropertyList
from .obj_type import INPUT_PROPERTIES, INPUT_TYPES, OUTPUT_PROPERTIES, OUTPUT_TYPES
from .reliability import Reliability
from .status_flags import StatusFlags

DEFAULT_RESOLUTION = 0.1
DEFAULT_PRIORITY_ARRAY: list[float | None] = [None] * 16


class BACnetObj(BaseBACnetObj):
    """Represent BACnet objects."""

    resolution: float = Field(
        default=DEFAULT_RESOLUTION,
        alias=str(ObjProperty.RESOLUTION.value),
        gt=0,
        description="""Indicates the smallest recognizable change in `Present_Value` in
        engineering units (read-only).""",
    )

    @validator("resolution", pre=True)
    def set_default_resolution_if_none(cls, value: Optional[float]) -> float:
        """None should be interpreted as default value 0.1 -- `pydantic` does not
        handle it.
        """
        # pylint: disable=no-self-argument
        if value is None:
            return DEFAULT_RESOLUTION
        if isinstance(value, float):
            return value
        raise ValueError("Invalid resolution")

    status_flags: StatusFlags = Field(
        default=StatusFlags(flags=0b0000),
        alias=str(ObjProperty.STATUS_FLAGS.value),
        description="""
        Status flags. represents four Boolean flags that indicate the general "health" of
        an value. Three of the flags are associated with the values of other properties of
        this object. A more detailed status could be determined by reading the properties
        that are linked to these flags. The relationship between individual flags is
        not defined by the protocol.""",
    )

    @validator("status_flags", pre=True)
    def cast_list(cls, value: list[bool]) -> StatusFlags:
        """Status flag stored as list of 4 booleans. Converts it to one integer."""
        # pylint: disable=no-self-argument
        if isinstance(value, list) and len(value) == 4:
            int_value = 0b0000
            for i, flag in enumerate(value):
                if not isinstance(flag, bool):
                    raise ValueError("Invalid flag")
                if flag:
                    int_value |= 1 << len(value) - 1 - i
            return StatusFlags(flags=int_value)
        if isinstance(value, int) and 0 <= value <= 15:
            return StatusFlags(flags=value)
        raise ValueError("Invalid StatusFlags")

    priority_array: list[Optional[float]] = Field(
        default=DEFAULT_PRIORITY_ARRAY,
        alias=str(ObjProperty.PRIORITY_ARRAY.value),
        max_items=16,
        min_items=16,
        description="""Priority array. This property is a read-only array that contains
        prioritized commands that are in effect for this object.""",
    )

    @validator("priority_array", pre=True)
    def set_default_priority_array_if_none(
        cls, value: list[float | None] | None
    ) -> list[float | None]:
        """None should be interpreted as default value 0.1 -- `pydantic` does not
        handle it.
        """
        # pylint: disable=no-self-argument
        if not value or value == [None]:
            return DEFAULT_PRIORITY_ARRAY

        return value

    reliability: Union[Reliability, str] = Field(
        default=Reliability.NO_FAULT_DETECTED,
        alias=str(ObjProperty.RELIABILITY.value),
        description="""Provides an indication of whether the `Present_Value` is
        "reliable" as far as the BACnet Device can determine and, if not, why.""",
    )

    @validator("reliability", pre=True)
    def try_cast_reliability(cls, value: Reliability | str) -> Reliability | str:
        # pylint: disable=no-self-argument
        if not value:
            return Reliability.NO_FAULT_DETECTED
        if isinstance(value, Reliability):
            return value
        try:
            # Receive `Reliability` | `str`, but trying detect known `Reliability`.
            return Reliability[snake_case(value).upper()]  # type: ignore
        except KeyError:
            return value

    segmentation_supported: bool = Field(
        default=True, alias=str(ObjProperty.SEGMENTATION_SUPPORTED.value)
    )
    property_list: BaseBACnetObjPropertyList = Field(  # type: ignore
        ...,
        alias=str(ObjProperty.PROPERTY_LIST.value),
        description="""This read-only property is a JSON of property identifiers, one
        property identifier  for each property that exists within the object. The standard
        properties are not included in the JSON.""",
    )
    present_value: Any = Field(
        default=None,
        alias=str(ObjProperty.PRESENT_VALUE.value),
        description="""Indicates the current value, in engineering units, of the `TYPE`.
        `Present_Value` shall be optionally commandable. If `Present_Value` is commandable
        for a given object instance, then the `Priority_Array` and `Relinquish_Default`
        properties shall also be present for that instance.

        The `Present_Value` property shall be writable when `Out_Of_Service` is TRUE.
        """,
    )
    verified_present_value: Union[float, str] = Field(default="null")
    updated: datetime = Field(default=None, alias="timestamp")
    changed: datetime = Field(default=None)

    unreachable_in_row: int = Field(default=0)
    existing: bool = Field(
        default=True,
        description="False if object not exists (incorrect object data on server).",
    )

    class Config:  # pylint: disable=missing-class-docstring
        arbitrary_types_allowed = True

    # # FIXME: hotfix
    # @validator("default_poll_period")
    # def set_default_poll_period(cls, value: float, values: dict) -> None:
    #     # pylint: disable=no-self-argument
    #     """Set default value to nested model."""
    #     if values["property_list"].poll_period is None:
    #         values["property_list"].poll_period = value
    #
    # # FIXME: hotfix
    # @validator("default_send_period")
    # def set_default_send_period(cls, value: int, values: dict) -> None:
    #     # pylint: disable=no-self-argument
    #     """Set default value to nested model."""
    #     if values["property_list"].send_period is None:
    #         values["property_list"].send_period = value

    @property
    def polling_properties(self) -> tuple[ObjProperty, ...]:
        if self.object_type in INPUT_TYPES:
            return INPUT_PROPERTIES
        if self.object_type in OUTPUT_TYPES:
            return OUTPUT_PROPERTIES
        raise NotImplementedError("Properties for other types not defined")

    def set_property(
        self, value: Any | Exception, prop: ObjProperty = ObjProperty.PRESENT_VALUE
    ) -> None:
        """Sets `presentValue` with round by `resolution`.
        Use it to set new `presentValue` by read from controller.

        # `pydantic` BaseModel not support parametrized descriptor, setter.
        # See:
        #     - https://github.com/samuelcolvin/pydantic/pull/679  # custom descriptor
        #     - https://github.com/samuelcolvin/pydantic/issues/935
        #     - https://github.com/samuelcolvin/pydantic/issues/1577
        #     - https://github.com/samuelcolvin/pydantic/pull/2625  # computed fields

        Args:
            prop: property to set
            value: value to set
        Raises:
            AttributeError: if property doesn't exist.
        """
        if not isinstance(prop, ObjProperty):
            raise ValueError("Invalid property")

        self.updated = datetime.now()

        # if prop is ObjProperty.priorityArray:
        #     value = self.convert_priority_array(priority_array=value)
        if prop is ObjProperty.STATUS_FLAGS:
            value = StatusFlags(flags=value)
        property_name = snake_case(prop.name)
        setattr(self, property_name, value)

    @staticmethod
    def to_mqtt_str(obj: BACnetObj) -> str:
        return (
            f"{obj.device_id} {obj.object_id} {obj.object_type.value} "
            f"{obj.present_value} {obj.status_flags}"
        )

    @staticmethod
    def to_http_str(obj: BACnetObj, disabled_flags: StatusFlags) -> str:
        str_ = f"{obj.object_id} {obj.object_type.value} {obj.present_value}"

        if obj.object_type in OUTPUT_TYPES and obj.priority_array:
            pa_str = obj.priority_array_to_http_str(priority_array=obj.priority_array)
            str_ += " " + pa_str

        status_flags_with_disabled = obj.status_flags.get_flags_with_disabled(
            disabled_flags=disabled_flags.flags
        )
        str_ += " " + str(status_flags_with_disabled.flags)

        reliability = obj.reliability

        if isinstance(reliability, Reliability):
            # `Reliability` is subclass of `Enum`, which has `value` attribute.
            reliability = str(obj.reliability.value)  # type: ignore
        if not isinstance(reliability, str):
            raise ValueError(f"Unexpected reliability type: {type(reliability)}")
        if reliability and not reliability.isspace():
            str_ += " " + reliability
        str_ += ";"
        return str_

    @staticmethod
    def priority_array_to_http_str(priority_array: list[float | None]) -> str:
        """Convert priority array tuple to str.

        Result example: ,,,,,,,,40.5,,,,,,49.2,
        """
        return ",".join(
            ["" if priority is None else str(priority) for priority in priority_array]
        )


def group_by_period(objs: list[BACnetObj]) -> dict[float, dict[tuple[int, int], BACnetObj]]:
    """Groups objects by poll period and insert them into device for polling."""
    groups: dict[float, dict[tuple[int, int], BACnetObj]] = {}

    for obj in objs:
        poll_period = obj.property_list.poll_period
        try:
            groups[poll_period][(obj.object_id, obj.object_type.value)] = obj
        except KeyError:
            groups[poll_period] = {(obj.object_id, obj.object_type.value): obj}
    return groups

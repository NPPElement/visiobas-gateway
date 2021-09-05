from datetime import datetime
from typing import Any, Optional, Union

from pydantic import Field, validator

from ...utils import snake_case
from .base_obj import BaseBACnetObj
from .obj_property import ObjProperty
from .obj_property_list import BACnetObjPropertyListJsonModel
from .obj_type import INPUT_PROPERTIES, INPUT_TYPES, OUTPUT_PROPERTIES, OUTPUT_TYPES
from .status_flags import StatusFlags

try:
    from bacpypes.basetypes import PriorityArray  # type: ignore
except ImportError as exc:
    raise NotImplementedError from exc


class BACnetObj(BaseBACnetObj):
    """Represent BACnet objects."""

    resolution: float = Field(
        default=0.1,
        alias=str(ObjProperty.resolution.prop_id),
        gt=0,
        description="""Indicates the smallest recognizable change in `Present_Value` in
        engineering units (read-only).""",
    )
    status_flags: StatusFlags = Field(
        default=StatusFlags(flags=0b0000),
        # alias=ObjProperty.statusFlags.id_str, # todo read from server?
        description="""
        Status flags. represents four Boolean flags that indicate the general "health" of
        an value. Three of the flags are associated with the values of other properties of
        this object. A more detailed status could be determined by reading the properties
        that are linked to these flags. The relationship between individual flags is
        not defined by the protocol.""",
    )
    priority_array: tuple[int] = Field(
        alias=str(ObjProperty.priorityArray.prop_id),
        description="""Priority array. This property is a read-only array that contains
        prioritized commands that are in effect for this object.""",
    )
    reliability: Union[int, str] = Field(
        default="",
        alias=str(ObjProperty.reliability.prop_id),
        description="""Provides an indication of whether the `Present_Value` is
        "reliable" as far as the BACnet Device can determine and, if not, why.""",
    )
    segmentation_supported: bool = Field(
        default=False, alias=str(ObjProperty.segmentationSupported.prop_id)
    )
    property_list: BACnetObjPropertyListJsonModel = Field(
        ...,
        alias=str(ObjProperty.propertyList.prop_id),
        description="""This read-only property is a JSON of property identifiers, one
        property identifier  for each property that exists within the object. The standard
        properties are not included in the JSON.""",
    )

    # FIXME: hotfix
    default_poll_period: Optional[float] = Field(
        default=None,
        description="Internal variable to set default value into propertyList",
    )

    # TODO: add usage
    default_send_period: Optional[int] = Field(
        default=None,
        description="Internal variable to set default value into propertyList",
    )

    present_value: Union[Any, Exception] = Field(
        default=None,
        description="""Indicates the current value, in engineering units, of the `TYPE`.
        `Present_Value` shall be optionally commandable. If `Present_Value` is commandable
        for a given object instance, then the `Priority_Array` and `Relinquish_Default`
        properties shall also be present for that instance.

        The `Present_Value` property shall be writable when `Out_Of_Service` is TRUE.
        """,
    )
    verified_present_value: Union[float, str] = Field(default="null")
    updated: datetime = Field(default=None)
    changed: datetime = Field(default=None)

    # exception: Optional[Exception] = None
    unreachable_in_row: int = Field(default=0)
    existing: bool = Field(
        default=True,
        description="False if object not exists (incorrect object data on server).",
    )

    class Config:  # pylint: disable=missing-class-docstring
        arbitrary_types_allowed = True

    # FIXME: hotfix
    @validator("default_poll_period")
    def set_default_poll_period(cls, value: float, values: dict) -> None:
        # pylint: disable=no-self-argument
        """Set default value to nested model."""
        if values["property_list"].poll_period is None:
            values["property_list"].poll_period = value

    # FIXME: hotfix
    @validator("default_send_period")
    def set_default_send_period(cls, value: int, values: dict) -> None:
        # pylint: disable=no-self-argument
        """Set default value to nested model."""
        if values["property_list"].send_period is None:
            values["property_list"].send_period = value

    @property
    def polling_properties(self) -> tuple[ObjProperty, ...]:
        if self.type in INPUT_TYPES:
            return INPUT_PROPERTIES
        if self.type in OUTPUT_TYPES:
            return OUTPUT_PROPERTIES
        raise NotImplementedError("Properties for other types not defined")

    def set_property_value(
        self, value: Union[Any, Exception], prop: ObjProperty = ObjProperty.presentValue
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
        self.updated = datetime.now()

        if prop is ObjProperty.priorityArray:
            value = self.convert_priority_array(priority_array=value)
        elif prop is ObjProperty.statusFlags:
            value = StatusFlags(flags=value)
        property_name = snake_case(prop.name)
        setattr(self, property_name, value)

    def to_mqtt_str(self) -> str:
        return "{0} {1} {2} {3} {4}".format(
            self.device_id,
            self.id,
            self.type.type_id,
            self.present_value,
            self.status_flags,
        )

    def to_http_str(self) -> str:
        str_ = "{0} {1} {2}".format(
            self.id,
            self.type.type_id,
            self.present_value,
        )
        if self.priority_array:
            pa_str = self._convert_pa_to_str(priority_array=self.priority_array)
            str_ += " " + pa_str

        str_ += " " + str(self.status_flags.for_http.flags)  # SF with disabled flags!

        if self.reliability and self.reliability != "no-fault-detected":
            str_ += " " + str(self.reliability)

        return str_

    @staticmethod
    def _convert_pa_to_str(priority_array: tuple) -> str:
        """Convert priority array tuple to str.

        Result example: ,,,,,,,,40.5,,,,,,49.2,
        """
        return ",".join(
            ["" if priority is None else str(priority) for priority in priority_array]
        )

    @staticmethod
    def convert_priority_array(priority_array: PriorityArray) -> tuple:
        """Converts `bacpypes.PriorityArray` as tuple."""
        priorities = [
            v[0] if k[0] != "null" else None
            for k, v in [
                zip(*priority_array.value[i].dict_contents().items())
                for i in range(1, priority_array.value[0] + 1)
            ]
        ]
        return tuple(priorities)

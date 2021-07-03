import asyncio
from datetime import datetime
from typing import Optional, Union

from BAC0.core.io.IOExceptions import UnknownObjectError
from pydantic import Field, BaseModel, PrivateAttr, validator, Json

from .base_obj import BaseBACnetObjModel
from .obj_property import ObjProperty
from .status_flags import StatusFlags


class BACnetObjPropertyListJsonModel(BaseModel):
    # property_list: BACnetObjPropertyListModel = Field(default=None)
    poll_period: Optional[float] = Field(default=None, alias='pollPeriod',
                                         description='Period to send data to server.')

    # TODO: add usage
    send_period: Optional[float] = Field(default=None, alias='sendPeriod',
                                         description='Period to send object to server.')

    # @validator('poll_period')
    # def set_default_poll_period_from_device(cls, v: Optional[float], values) -> float:
    #     return v or values['dev_property_list'].poll_period

    def __str__(self) -> str:
        return str(self.__dict__)

    def __repr__(self) -> str:
        return str(self)


class BACnetObj(BaseBACnetObjModel):
    resolution: Optional[Union[int, float]] = Field(
        default=None, alias=ObjProperty.resolution.id_str, gt=0,
        description='''
        Indicates the smallest recognizable change in `Present_Value` in 
        engineering units (read-only).''')
    # pv: LastValue = Field(default=LastValue(resolution=resolution),
    #                       alias=ObjProperty.presentValue.id_str,
    #                       description='Present value')
    sf: StatusFlags = Field(
        default=StatusFlags(flags=0b0000),
        # alias=ObjProperty.statusFlags.id_str, # todo read from server?
        description='''
        Status flags. represents four Boolean flags that indicate the general "health" of 
        an value. Three of the flags are associated with the values of other properties of 
        this object. A more detailed status could be determined by reading the properties 
        that are linked to these flags. The relationship between individual flags is 
        not defined by the protocol.''')
    pa: Optional[Union[str, tuple]] = Field(
        alias=ObjProperty.priorityArray.id_str,
        description='''
        Priority array. This property is a read-only array that contains prioritized 
        commands that are in effect for this object.''')
    reliability: Optional[Union[int, str]] = Field(
        default=None,
        alias=ObjProperty.reliability.id_str,
        description='''
        Provides an indication of whether the `Present_Value` is "reliable" as far as 
        the BACnet Device can determine and, if not, why.''')

    segmentation_supported: bool = Field(default=False,
                                         alias=ObjProperty.segmentationSupported.id_str)
    property_list: Json[BACnetObjPropertyListJsonModel] = Field(
        ..., alias=ObjProperty.propertyList.id_str, description='''
        This read-only property is a JSON of property identifiers, one property identifier 
        for each property that exists within the object. The standard properties are not 
        included in the JSON.''')

    # FIXME: hotfix
    default_poll_period: Optional[float] = Field(
        default=None,
        description='Internal variable to set default value into propertyList')

    # TODO: add usage
    default_send_period: Optional[int] = Field(
        default=None,
        description='Internal variable to set default value into propertyList')

    _last_value: Optional[Union[int, float, str]] = PrivateAttr()
    _updated_at: Optional[datetime] = PrivateAttr()

    # exception: Optional[Exception] = None
    _unreachable_in_row: int = PrivateAttr(default=0)

    # False if object not exists (incorrect object data on server).
    _existing: bool = PrivateAttr(default=True)

    class Config:
        arbitrary_types_allowed = True

    @validator('resolution')
    def validate_resolution(cls, v: Optional[Union[int, float]], values
                            ) -> Optional[Union[int, float]]:
        if values['type'].is_analog and not v:
            return 0.1  # default resolution value
        return v

    # FIXME: hotfix
    @validator('default_poll_period')
    def set_default_poll_period(cls, v, values) -> None:
        """Set default value to nested model."""
        if values['property_list'].poll_period is None:
            values['property_list'].poll_period = v

    # FIXME: hotfix
    @validator('default_send_period')
    def set_default_send_period(cls, v, values) -> None:
        """Set default value to nested model."""
        if values['property_list'].send_period is None:
            values['property_list'].send_period = v

    @property
    def existing(self) -> bool:
        return self._existing

    @property
    def unreachable_in_row(self) -> int:
        return self._unreachable_in_row

    @property
    def pv(self) -> Optional[Union[int, float, str]]:
        """Indicates the current value, in engineering units, of the `TYPE`.
        `Present_Value` shall be optionally commandable. If `Present_Value` is commandable
        for a given object instance, then the `Priority_Array` and `Relinquish_Default`
        properties shall also be present for that instance.

        The `Present_Value` property shall be writable when `Out_Of_Service` is TRUE.
        """
        return self._last_value

    def set_exc(self, exc: Exception) -> None:
        """Sets properties related with exception."""
        self._unreachable_in_row += 1
        self._last_value = 'null'

        if isinstance(exc, (asyncio.TimeoutError, asyncio.CancelledError)):
            self.reliability = 'timeout'

        # todo: add modbus non-existent exceptions
        elif isinstance(exc, (UnknownObjectError,)):
            self._existing = False
            self.reliability = 'non-existent-object'
        elif isinstance(exc, (TypeError, ValueError)):
            self.reliability = 'decode-error'
        else:
            # RELIABILITY_LEN_LIMIT = 50
            str_exc = exc.__class__.__name__  # str(exc)[-RELIABILITY_LEN_LIMIT:]
            self.reliability = str_exc

        self.reliability = self.reliability.strip().replace(
            ' ', '-').replace(',', '-').replace(':', '-').replace(
            '.', '-').replace('/', '-').replace('[', '').replace(']', '')

    def set_pv(self, value: Optional[Union[int, float, str]]) -> None:
        """Sets presentValue with round by resolution.
        Use it to set new presentValue by read from controller.

        In verifier case please use _last_value

        # `pydantic` BaseModel not support parametrized descriptor, setter.
        # See:
        #     - https://github.com/samuelcolvin/pydantic/pull/679  # custom descriptor
        #     - https://github.com/samuelcolvin/pydantic/issues/935
        #     - https://github.com/samuelcolvin/pydantic/issues/1577
        #     - https://github.com/samuelcolvin/pydantic/pull/2625  # computed fields

        Args:
            value: presentValue of object
        """
        assert isinstance(value, (int, float, str))

        def _round(value_: Union[float, int],
                   resolution: Union[int, float]) -> float:
            assert isinstance(resolution, (int, float))

            rounded = round(value_ / resolution) * resolution

            if isinstance(resolution, int):
                return rounded
            elif isinstance(resolution, float):
                whole_part, fractional_part = str(resolution).split('.', maxsplit=1)
                digits = len(fractional_part)
                return round(rounded, ndigits=digits)

        self._unreachable_in_row = 0
        self._updated_at = datetime.now()
        self.reliability = None

        if isinstance(value, (float, int)) and self.type.is_analog:
            self._last_value = _round(value_=value, resolution=self.resolution)
        elif isinstance(value, str) or value is None or self.type.is_discrete:
            self._last_value = value
        else:
            raise ValueError(f'Unexpected params: {locals()}')

    def __str__(self) -> str:
        return self.__class__.__name__ + str(self.__dict__)

    def __repr__(self) -> str:
        return str(self)

    def to_mqtt_str(self) -> str:
        return '{0} {1} {2} {3} {4}'.format(self.device_id, self.id, self.type.id,
                                            self.pv, self.sf, )

    def to_http_str(self) -> str:
        str_ = '{0} {1} {2}'.format(self.id, self.type.id, self.pv, )
        if self.pa:
            pa_str = self._convert_pa_to_str(pa=self.pa)
            str_ += ' ' + pa_str

        str_ += ' ' + str(self.sf.for_http.flags)  # SF with disabled flags!

        if self.reliability and self.reliability != 'no-fault-detected':
            str_ += ' ' + str(self.reliability)

        return str_

    @staticmethod
    def _convert_pa_to_str(pa: tuple) -> str:
        """Convert priority array tuple to str.

        Result example: ,,,,,,,,40.5,,,,,,49.2,
        """
        return ','.join(
            ['' if priority is None else str(priority)
             for priority in pa]
        )

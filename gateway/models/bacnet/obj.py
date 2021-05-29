from datetime import datetime
from typing import Optional, Union

from pydantic import Field, BaseModel

from .base_obj import BaseBACnetObjModel
from .obj_property import ObjProperty
from .status_flags import StatusFlags


class BACnetObjPropertyListModel(BaseModel):
    send_interval: float = Field(default=60, alias='sendPeriod',
                                 description='Period to internal object poll')

    def __repr__(self) -> str:
        return str(self.__dict__)


class BACnetObjPropertyListJsonModel(BaseModel):
    property_list: BACnetObjPropertyListModel = Field(default=None)

    def __str__(self) -> str:
        return str(self.__dict__)

    def __repr__(self) -> str:
        return str(self)


class LastValue:
    def __init__(self, resolution: float, value=None):
        self.resolution = resolution

        whole_part, fractional_part = str(resolution).split('.', maxsplit=1)
        self.ndigits = len(fractional_part)

        self.value = value
        self.updated: datetime = None  # when it was updated

    def __get__(self, instance, owner):
        return self.value

    def __set__(self, instance, value: Optional[Union[float, int, str]]) -> None:
        self.updated = datetime.now()
        if isinstance(value, (float, int)):
            self.value = self._round(value=value)
        elif isinstance(value, str) or value is None:
            self.value = value
        else:
            raise NotImplemented

    def _round(self, value: Union[float, int]) -> float:
        return round(
            round(value / self.resolution) * self.resolution,
            ndigits=self.ndigits)


class BACnetObj(BaseBACnetObjModel):
    resolution: Optional[float] = Field(default=0.1, alias=ObjProperty.resolution.id_str)
    # pv: LastValue = Field(default=LastValue(resolution=resolution),
    #                       alias=ObjProperty.presentValue.id_str,
    #                       description='Present value')
    sf: StatusFlags = Field(default=StatusFlags(flags=0b0000),
                            # alias=ObjProperty.statusFlags.id_str, # todo read from server?
                            description='Status flags')
    pa: Optional[Union[str, tuple]] = Field(alias=ObjProperty.priorityArray.id_str,
                                            description='Priority array')
    reliability: Optional[Union[int, str]] = Field(default=None,
                                                   alias=ObjProperty.reliability.id_str)
    pv = LastValue(resolution=resolution)

    # todo find public property
    # send_interval: Optional[float] = Field(default=60,
    #                                        alias=ObjProperty.updateInterval.id_str)

    segmentation_supported: bool = Field(default=False,
                                         alias=ObjProperty.segmentationSupported.id_str)
    property_list: BACnetObjPropertyListJsonModel = Field(
        ..., alias=ObjProperty.propertyList.id_str)

    # value = Field(default=LastValue(resolution=resolution, value=None))
    exception: Optional[Exception] = None

    class Config:
        arbitrary_types_allowed = True
        keep_untouched = (LastValue, )

    def __str__(self) -> str:
        return self.__class__.__name__ + str(self.__dict__)

    def __repr__(self) -> str:
        return str(self)

    def to_mqtt_str(self) -> str:
        return '{0} {1} {2} {3} {4}'.format(self.device_id,
                                            self.id,
                                            self.type.id,
                                            self.pv,
                                            self.sf, )

    def to_http_str(self) -> str:
        str_ = '{0} {1} {2}'.format(self.id,
                                    self.type.id,
                                    self.pv, )
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

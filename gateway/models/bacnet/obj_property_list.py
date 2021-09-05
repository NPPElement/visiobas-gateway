from pydantic import BaseModel, Field


class BACnetObjPropertyListJsonModel(BaseModel):
    """Represent PropertyList (371) for BACnet objects."""

    poll_period: float = Field(
        default=None, alias="pollPeriod", description="Period to send data to server."
    )
    # TODO: add usage
    send_period: float = Field(
        default=None, alias="sendPeriod", description="Period to send object to server."
    )

    # @validator('poll_period')
    # def set_default_poll_period_from_device(cls, v: Optional[float], values) -> float:
    #     return v or values['dev_property_list'].poll_period

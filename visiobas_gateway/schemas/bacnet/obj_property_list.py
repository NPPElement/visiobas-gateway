from abc import ABC

from pydantic import BaseModel, Field


class BaseBACnetObjPropertyList(BaseModel, ABC):
    """Represent PropertyList (371) for BACnet objects."""

    poll_period: float = Field(
        default=90, ge=0, alias="pollPeriod", description="Period to send data to server."
    )
    # TODO: add usage
    # send_period: float = Field(
    #     default=None, alias="sendPeriod", description="Period to send object to server."
    # )

from abc import ABC

from pydantic import BaseModel, Field

from ..send_methods import SendMethod


class BaseBACnetObjPropertyList(BaseModel, ABC):
    """Represent PropertyList (371) for BACnet objects."""

    poll_period: float = Field(
        default=90,
        ge=0,
        alias="pollPeriod",
        description="Period to read data from devices.",
    )
    send_period: float = Field(
        default=90, ge=0, alias="sendPeriod", description="Period to send object to server."
    )
    send_methods: list[SendMethod] = Field(
        default=[SendMethod.HTTP], description="Methods used to send objects"
    )

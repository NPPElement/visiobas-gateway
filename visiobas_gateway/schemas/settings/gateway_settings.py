from pydantic import BaseSettings, Field, PositiveInt, validator

from ..bacnet.priority import Priority


class GatewaySettings(BaseSettings):
    """Main settings of gateway."""

    update_period: int = Field(default=3600, ge=1800)
    unreachable_reset_period: int = Field(default=1800, ge=900)
    unreachable_threshold: int = Field(
        default=3,
        ge=1,
        description="Number of unsuccessful attempts to read object to "
        "mark it as unreachable.",
    )
    override_threshold: Priority = Field(
        default=Priority.MANUAL_OPERATOR,
        description=(
            "If priority is equal or greater than this value - "
            "verifier sets the `OVERRIDEN` flag."
        ),
    )
    poll_device_ids: list[PositiveInt] = Field(
        ..., min_items=1, description="List of polling device ids"
    )

    @validator("poll_device_ids")
    def remove_duplicated_ids(cls, value: list[PositiveInt]) -> list[PositiveInt]:
        # pylint: disable=no-self-argument
        return sorted(list(set(value)))

    class Config:  # pylint: disable=missing-class-docstring
        env_prefix = "GTW_"
        env_file = ".env"
        env_file_encoding = "utf-8"

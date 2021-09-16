from pydantic import AnyHttpUrl, BaseSettings, Field, PositiveInt, validator


class GatewaySettings(BaseSettings):
    """Main settings of visiobas_gateway."""

    # todo: solve problem with 'polling by'
    # address: IPv4Address = Field(
    #     ..., description="Gateway's address. "
    #                      "Uses to set 'polled by' in polling device object.")
    update_period: int = Field(default=3600, ge=1800)
    unreachable_reset_period: int = Field(default=1800, ge=900)
    unreachable_threshold: int = Field(
        default=3,
        ge=1,
        description="Number of unsuccessful attempts to read object to "
        "mark it as unreachable.",
    )
    override_threshold: int = Field(
        default=8,
        gt=0,
        le=16,
        description=(
            "If priority is equal or greater than this value - "
            "verifier sets the OVERRIDEN flag."
        ),
    )
    poll_device_ids: list[PositiveInt] = Field(..., min_items=1)

    # modbus_sync: bool = Field(
    #     default=True, description="Use synchronous client for Modbus protocol."
    # )
    mqtt_enable: bool = Field(
        default=False, description="Initialize connection by mqtt"  # todo: temp
    )
    api_url: AnyHttpUrl = Field(default="http://0.0.0.0:7070")
    api_priority: int = Field(
        default=11,
        ge=0,
        le=16,
        description="Priority that sets when writing through the visiobas_gateway API.",
    )

    class Config:  # pylint: disable=missing-class-docstring
        env_prefix = "GTW_"
        env_file = ".env"
        env_file_encoding = "utf-8"

    @validator("poll_device_ids")
    def remove_duplicate_device_ids(cls, value: list[PositiveInt]) -> list[PositiveInt]:
        # pylint: disable=no-self-argument
        return list(set(value))

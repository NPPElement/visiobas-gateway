from pydantic import (Field, BaseSettings, AnyHttpUrl)


class GatewaySettings(BaseSettings):
    # todo: solve problem with 'polling by'
    # address: IPv4Address = Field(
    #     ..., description="Gateway's address. "
    #                      "Uses to set 'polled by' in polling device object.")

    update_period: int = Field(default=3600, ge=1800)
    unreachable_reset_period: int = Field(default=1800, ge=900)
    unreachable_threshold: int = Field(
        default=3, ge=1, description='Number of unsuccessful attempts to read object to '
                                     'mark it as unreachable.')
    override_threshold: int = Field(
        default=8, gt=0, le=16,
        description=('If priority is equal or greater than this value - '
                     'verifier sets the OVERRIDEN flag.'))

    poll_device_ids: list[int] = Field(..., min_items=1)

    modbus_sync: bool = Field(default=True,
                              description='Use synchronous client for Modbus protocol.')
    mqtt_enable: bool = Field(default=False, # todo: temp
                              description='Initialize connection by mqtt')

    api_url: AnyHttpUrl = Field(default='http://0.0.0.0:7070')
    api_priority: int = Field(
        default=11, ge=0, le=16,
        description='Priority that sets when writing through the gateway API.')

    class Config:
        env_prefix = 'GTW_'
        env_file = '.env'
        env_file_encoding = 'utf-8'

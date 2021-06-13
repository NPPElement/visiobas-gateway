from pydantic import BaseSettings, Field, AnyUrl


class MQTTSettings(BaseSettings):
    url: AnyUrl = Field(...)

    qos: int = Field(default=0, ge=0, le=2)
    retain: bool = Field(default=True)
    keepalive: int = Field(default=60, ge=1)

    topics_sub: list[str] = Field(default=None)

    class Config:
        # arbitrary_types_allowed = True
        env_prefix = 'GTW_MQTT_'
        env_file = '.env'
        env_file_encoding = 'utf-8'

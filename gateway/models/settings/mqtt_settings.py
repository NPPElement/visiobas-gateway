import uuid
from typing import Optional

import paho.mqtt.client as mqtt
from pydantic import AnyUrl, BaseSettings, Field, validator


class MQTTSettings(BaseSettings):
    url: AnyUrl = Field(...)

    qos: int = Field(default=0, ge=0, le=2)
    retain: bool = Field(default=True)
    keepalive: int = Field(default=60, ge=1)

    topics_sub: list[str] = Field(default=None)
    client_id: Optional[str] = Field(default=None)  # todo add factory/validation

    # todo: add certificate

    @validator("client_id")
    def create_client_id(cls, v: Optional[str]) -> str:
        return v or mqtt.base62(uuid.uuid4().int, padding=22)

    class Config:
        # arbitrary_types_allowed = True
        env_prefix = "GTW_MQTT_"
        env_file = ".env"
        env_file_encoding = "utf-8"

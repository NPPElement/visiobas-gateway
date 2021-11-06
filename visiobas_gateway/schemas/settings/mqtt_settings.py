from __future__ import annotations

import uuid

import paho.mqtt.client as mqtt  # type: ignore
from pydantic import AnyUrl, BaseSettings, Field, validator

from ..mqtt import Qos


class MQTTSettings(BaseSettings):
    """Settings of MQTT client."""

    enable: bool = Field(default=False, description="Flag for MQTT client activation.")
    url: AnyUrl = Field(...)

    @validator("url")
    def check_required(cls, value: AnyUrl) -> AnyUrl:
        # pylint: disable=no-self-argument
        if not value.port:
            raise ValueError("Port required.")
        return value

    qos: Qos = Field(default=Qos.AT_MOST_ONCE_DELIVERY)
    retain: bool = Field(default=True)
    keepalive: int = Field(default=60, ge=1)

    topics_sub: list[str] = Field(default=[])

    @property
    def topics_sub_with_qos(self) -> list[tuple[str, int]]:
        """Topics to subscribe."""
        return [(topic, self.qos) for topic in self.topics_sub]

    client_id: str = Field(default=None)

    # @validator("client_id", pre=True)
    # def create_client_id(cls, value: str | None) -> str:
    #     # pylint: disable=no-self-argument
    #     return value or mqtt.base62(uuid.uuid4().int, padding=22)

    # todo: add security

    class Config:  # pylint: disable=missing-class-docstring
        allow_mutation = False
        # arbitrary_types_allowed = True
        env_prefix = "GTW_MQTT_"
        env_file = ".env"
        env_file_encoding = "utf-8"

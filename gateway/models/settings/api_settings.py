from typing import Optional

from pydantic import AnyHttpUrl, BaseSettings, Field


class ApiSettings(BaseSettings):
    """Settings of API application."""

    url: AnyHttpUrl = Field(default="http://0.0.0.0:7070", description="Url to run API.")
    priority: int = Field(default=11, description="Priority to write through gateway API.")

    class Config:  # pylint: disable=missing-class-docstring
        env_prefix = "GTW_API_"
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def host(self) -> str:
        return self.url.host

    @property
    def port(self) -> Optional[int]:
        if self.url.port:
            return int(self.url.port)
        return None

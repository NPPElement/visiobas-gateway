from pydantic import BaseSettings, Field

from .http_server import HttpServerConfig


class HttpSettings(BaseSettings):
    """Settings of HTTP client."""

    timeout: int = Field(default=10)
    next_attempt: int = Field(default=60)

    server_get: HttpServerConfig = Field(...)
    servers_post: list[HttpServerConfig] = Field(..., min_items=1)

    class Config:  # pylint: disable=missing-class-docstring
        allow_mutation = False
        arbitrary_types_allowed = True
        env_prefix = "GTW_HTTP_"
        env_file = ".env"
        env_file_encoding = "utf-8"

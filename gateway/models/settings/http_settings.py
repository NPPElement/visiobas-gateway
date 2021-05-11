from pydantic import Field, BaseSettings

from .http_server import HTTPServerConfig


class HTTPSettings(BaseSettings):
    timeout: int = Field(default=10)  # todo: get from main properties
    retry: int = Field(default=60)

    server_get: HTTPServerConfig = Field(...)
    servers_post: list[HTTPServerConfig] = Field(...)

    class Config:
        arbitrary_types_allowed = True
        env_prefix = 'GW_HTTP_'
        env_file = '.env'
        env_file_encoding = 'utf-8'

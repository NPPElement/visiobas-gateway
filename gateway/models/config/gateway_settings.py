from pathlib import Path

from pydantic import (Field, DirectoryPath, BaseSettings, AnyHttpUrl, validator)

from models.config.http_settings import HTTPSettings


class GatewaySettings(BaseSettings):
    update_period: int = Field(default=3600, ge=1800)
    override_threshold: int = Field(
        default=8, gt=0, le=16,
        description=('If priority is equal or greater than this value - '
                     'verifier sets the OVERRIDEN flag'))
    poll_device_ids: list[int] = Field(..., min_items=1)

    api_url: AnyHttpUrl = Field(default='http://localhost:7070')

    # Paths
    # config_path: str = Field(default='config',
    #                          description='Path to the config directory from the base path.')

    # http_config_path: FilePath = Field(default=config_dir / 'http.json')
    # mqtt_config_path: FilePath = Field(default=config_dir / 'mqtt.json')

    # http: HTTPSettings = Field(...)
    # http: HTTPSettings = HTTPSettings(_env_file='...config/http.env')
    # str = Field(default='http.env')
    # mqtt_env_file: str = Field(default='mqtt.env')

    # mqtt: Optional = Field(default=None)  # todo

    class Config:
        env_prefix = 'GW_'
        env_file = '.env'
        env_file_encoding = 'utf-8'

    # @property
    # def base_dir(self) -> DirectoryPath:
    #     return Path(__file__).resolve().parent.parent.parent.parent
    #
    # @property
    # def config_dir(self) -> DirectoryPath:
    #     return self.base_dir / self.config_path

    # @property
    # def http(self) -> HTTPSettings:
    #     env_path = self.config_dir / 'http.env'
    #     return HTTPSettings(_env_file=env_path)

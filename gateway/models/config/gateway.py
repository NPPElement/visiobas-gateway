import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, validator, DirectoryPath, FilePath
from yarl import URL

from .http import VisioHTTPConfig


class VisioGatewayConfig(BaseModel):
    update_period: int = Field(default=3600, ge=1800)
    verifier_override_threshold: int = Field(default=8, gt=0, le=16,
                                             description=(
                                                 'if priority is equal or greater than '
                                                 'this value - verifier sets '
                                                 'the OVERRIDEN flag'))
    api_url: HttpUrl = Field(default='http://localhost:7070')

    # Paths
    _BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
    config_dir: DirectoryPath = Field(
        default=Path(os.getenv('CONFIG_DIR', _BASE_DIR / 'config')))

    http_config_path: FilePath = Field(default=config_dir / 'http.json')
    mqtt_config_path: FilePath = Field(default=config_dir / 'mqtt.json')

    http: Optional[VisioHTTPConfig] = Field(
        default=VisioHTTPConfig.parse_raw(http_config_path.read_text()))
    mqtt: Optional = Field(default=None)  # todo

    @validator('api_url')
    def cast_url(cls, v: HttpUrl) -> URL:
        return URL(v)

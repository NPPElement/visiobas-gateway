from pydantic import BaseModel, Field

from .http_node import HTTPNodeConfig


class VisioHTTPClientConfig(BaseModel):
    timeout: int = Field(default=10)  # todo: get from main properties
    retry: int = Field(default=60)

    get_node: HTTPNodeConfig
    post_nodes: dict[str, HTTPNodeConfig]

    class Config:
        arbitrary_types_allowed = True



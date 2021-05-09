from typing import Union

from pydantic import BaseModel, Field, validator

from .http_node import HTTPNodeConfig


class VisioHTTPConfig(BaseModel):
    timeout: int = Field(default=10)  # todo: get from main properties
    retry: int = Field(default=60)

    get_node: HTTPNodeConfig
    # in validation: dict[str, HTTPNodeConfig] -> set[HTTPNodeConfig]
    post_nodes: Union[dict[str, HTTPNodeConfig], set[HTTPNodeConfig]]

    class Config:
        arbitrary_types_allowed = True

    @validator('post_nodes')
    def dict_to_list(cls, v: dict[int, HTTPNodeConfig]) -> set[HTTPNodeConfig]:
        return set(v.values())

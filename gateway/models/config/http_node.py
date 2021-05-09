from typing import Optional

from pydantic import Field, BaseModel

from .http_server import HTTPServerConfig


class HTTPNodeConfig(BaseModel):
    """Represent Visio HTTP node (primary server + mirror server)."""

    # __slots__ = ['primary', 'mirror', 'cur_server', ]

    primary: HTTPServerConfig = Field(...)
    mirror: Optional[HTTPServerConfig] = Field(default=None)

    # current: HTTPServerConfig = Field(default=primary)

    # def __init__(self, primary: HTTPServerConfig,
    #              mirror: Optional[HTTPServerConfig] = None):
    #     self.primary = primary
    #     self.mirror = mirror
    #
    #     self.cur_server = primary

    @property
    def is_authorized(self) -> bool:
        return self.primary.is_authorized

    def __str__(self) -> str:
        return str(self.primary)

    def __repr__(self) -> str:
        return repr(self.primary)

    def switch_server(self) -> bool:
        """Switches communication to mirror if the primary server is unavailable.

        Returns:
            Was switched or not
        """
        if self.mirror:
            self.primary, self.mirror = self.mirror, self.primary
            return True
        return False

    # @classmethod
    # def from_dict(cls, config: dict):
    #     """Create HTTP node from dict."""
    #     primary_server_cfg = HTTPServerConfig(**config['primary'])
    #     try:
    #         mirror_server_cfg = HTTPServerConfig(**config['mirror'])
    #     except KeyError:
    #         mirror_server_cfg = None
    #
    #     return cls(primary=primary_server_cfg,
    #                mirror=mirror_server_cfg)

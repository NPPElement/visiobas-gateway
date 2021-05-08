from typing import Optional

from ...models import HTTPServerConfig


class VisioHTTPNode:
    """Represent Visio HTTP node (primary server + mirror server)."""

    __slots__ = ['primary', 'mirror', 'cur_server', ]

    def __init__(self, primary: HTTPServerConfig,
                 mirror: Optional[HTTPServerConfig] = None):
        self.primary = primary
        self.mirror = mirror

        self.cur_server = primary

    @property
    def is_authorized(self) -> bool:
        return self.cur_server.is_authorized

    def __str__(self) -> str:
        return str(self.cur_server)

    def __repr__(self) -> str:
        return repr(self.cur_server)

    def switch_to_mirror(self) -> bool:
        """Switches communication to mirror if the primary server is unavailable.

        Returns:
            Was switched or not
        """
        if self.mirror:
            self.cur_server = self.mirror
            return True
        return False

    @classmethod
    def from_dict(cls, config: dict):
        """Create HTTP node from dict."""
        primary_server_cfg = HTTPServerConfig(**config['primary'])
        try:
            mirror_server_cfg = HTTPServerConfig(**config['mirror'])
        except KeyError:
            mirror_server_cfg = None

        return cls(primary=primary_server_cfg,
                   mirror=mirror_server_cfg)

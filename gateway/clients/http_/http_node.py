from typing import Optional

from .http_config import HTTPServerConfig


class VisioHTTPNode:
    """Represent Visio HTTP node (primary server + mirror server)."""

    def __init__(self, primary: HTTPServerConfig,
                 mirror: Optional[HTTPServerConfig] = None):
        self.primary = primary
        self.mirror = mirror

        self.cur_server = primary

    @property
    def is_authorized(self) -> bool:
        return self.cur_server.is_authorized

    def __repr__(self) -> str:
        # _auth_status = f'Authorized' if self.is_authorized else 'Unauthorized'
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

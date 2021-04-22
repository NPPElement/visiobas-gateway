from .http_config import VisioHTTPConfig


class VisioHTTPNode:
    """Represent Visio HTTP node (primary server + mirror server)."""

    def __init__(self, primary: VisioHTTPConfig, mirror: VisioHTTPConfig):
        self.primary = primary
        self.mirror = mirror

        self.cur_server = primary

    @property
    def is_authorized(self) -> bool:
        return self.cur_server.is_authorized

    def __repr__(self) -> str:
        _auth_status = f'Authorized' if self.is_authorized else 'Unauthorized'
        return str(self.cur_server)

    def switch_to_mirror(self) -> None:
        """ Switches communication to mirror if the primary server is unavailable """
        self.cur_server = self.mirror

    @classmethod
    def from_dict(cls, cfg: dict):
        """Create HTTP node from dict."""
        return cls(primary=VisioHTTPConfig.from_dict(cfg=cfg['primary']),
                   mirror=VisioHTTPConfig.from_dict(cfg=cfg['mirror'])
                   )

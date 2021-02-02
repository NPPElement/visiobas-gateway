from hashlib import md5

from gateway.logs import get_file_logger

_log = get_file_logger(logger_name=__name__,
                       size_bytes=50_000_000
                       )


class VisioHTTPConfig:
    """Represent parameters for Visio HTTP server."""

    # That class allows to create only one instance for each server's params
    _instances = {}  # keeps instances references

    __slots__ = ('_login', '_password_md5', 'host', 'port',
                 '_bearer_token', '_user_id', '_auth_user_id',
                 'is_connected', 'is_authorized'
                 )

    def __new__(cls, *args, **kwargs):
        # Used kwargs because __init__ accept args by key
        _args_hash = hash((kwargs.get('login'),
                           kwargs.get('password'),
                           kwargs.get('host'),
                           kwargs.get('port')
                           ))
        if cls._instances.get(_args_hash) is None:
            cls._instances[_args_hash] = super().__new__(cls)
        return cls._instances[_args_hash]

    def __init__(self, login: str, password: str, host: str, port: int):
        self.host = host
        self.port = port

        self._login = login
        self._password_md5 = md5(password.encode()).hexdigest()

        self._bearer_token = None
        self._user_id = None
        self._auth_user_id = None

        self.is_connected = True
        self.is_authorized = False

    def set_auth_data(self, bearer_token: str, user_id: int, auth_user_id: int) -> None:
        # TODO validate data
        self._bearer_token = bearer_token
        self._user_id = user_id
        self._auth_user_id = auth_user_id

        self.is_authorized = True

    # def delete_auth_data(self) -> None:
    #     self._bearer_token = None
    #     self._user_id = None
    #     self._auth_user_id = None
    #
    #     self.is_authorized = False

    @property
    def base_url(self) -> str:
        return 'http://' + ':'.join((self.host, str(self.port)))

    @property
    def auth_payload(self) -> dict[str, str]:
        data = {'login': self._login,
                'password': self._password_md5
                }
        return data

    @property
    def auth_headers(self) -> dict[str, str]:
        if isinstance(self._bearer_token, str):
            headers = {'Authorization': f'Bearer {self._bearer_token}'
                       }
            return headers

    def __repr__(self) -> str:
        _auth = 'Authorized' if self.is_authorized else 'Unauthorized'
        return f'<{self.__class__.__name__}: {_auth}:{self.host} [{self._login}]>'

    @classmethod
    def create_from_dict(cls, cfg: dict):
        """Create HTTP config for server from dict."""
        return cls(login=cfg['login'],
                   password=cfg['password'],
                   host=cfg['host'],
                   port=cfg.get('port', 8080)
                   )


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
        _is_authorized = f'Authorized' if self.is_authorized else 'Unauthorized'
        return f'<{self.__class__.__name__}: {_is_authorized}: {self.cur_server}>'

    def switch_to_mirror(self) -> None:
        """ Switches communication to mirror if the primary server is unavailable """
        self.cur_server = self.mirror

    @classmethod
    def create_from_dict(cls, cfg: dict):
        """Create HTTP node from dict."""
        return cls(primary=VisioHTTPConfig.create_from_dict(cfg=cfg['primary']),
                   mirror=VisioHTTPConfig.create_from_dict(cfg=cfg['mirror'])
                   )

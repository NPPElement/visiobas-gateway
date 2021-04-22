from hashlib import md5


class VisioHTTPConfig:
    """
    Represent parameters for Visio HTTP server.
    Singleton.
    """

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

        # self.is_connected = True
        self.is_authorized = False

    def __repr__(self) -> str:
        _auth_status = 'Authorized' if self.is_authorized else 'Unauthorized'
        return f'<[{_auth_status}]:{self.host}>'

    def set_auth_data(self, bearer_token: str, user_id: int, auth_user_id: int) -> None:
        # TODO validate data
        self._bearer_token = bearer_token
        self._user_id = user_id
        self._auth_user_id = auth_user_id

        self.is_authorized = True

    def clear_auth_data(self) -> None:
        self._bearer_token = None
        self._user_id = None
        self._auth_user_id = None

        self.is_authorized = False

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

    @classmethod
    def from_dict(cls, cfg: dict):
        """Create HTTP config for server from dict."""
        return cls(login=cfg['login'],
                   password=cfg['password'],
                   host=cfg['host'],
                   port=cfg.get('port', 8080)
                   )

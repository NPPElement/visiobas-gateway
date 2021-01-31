from hashlib import md5
from os import environ

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
        return f'<VisioHTTPConfig: {_auth}:{self.host} [{self._login}]>'

    @classmethod
    def read_from_env(cls, var_root: str):
        """ Creates a VisioHTTPServerConfig instance based on environment variables """
        try:
            return cls(login=environ[f'HTTP_{var_root}_LOGIN'],
                       password=environ[f'HTTP_{var_root}_PASSWORD'],
                       host=environ[f'HTTP_{var_root}_HOST'],
                       port=int(environ[f'HTTP_{var_root}_PORT']),
                       )
        except KeyError:
            _log.warning(f'{cls.__name__} cannot be read form environment variables.')
            raise EnvironmentError(
                "Please set the server parameters in environment variables:\n"
                f"'HTTP_{var_root}_HOST'\n"
                f"'HTTP_{var_root}_PORT'\n"
                f"'HTTP_{var_root}_LOGIN'\n"
                f"'HTTP_{var_root}_PASSWORD'"
            )


class VisioHTTPNode:
    """Represent Visio HTTP node (primary server + mirror server)."""

    def __init__(self, main: VisioHTTPConfig, mirror: VisioHTTPConfig):
        self.primary = main
        self.mirror = mirror

        self.cur_server = main

    @property
    def is_authorized(self) -> bool:
        return self.cur_server.is_authorized

    def __repr__(self) -> str:
        _is_authorized = f'Authorized' if self.is_authorized else 'Unauthorized'
        return f'<VisioHTTPNode: {_is_authorized}: {self.cur_server}>'

    def switch_to_mirror(self) -> None:
        """ Switches communication to mirror if the primary server is unavailable """
        self.cur_server = self.mirror

    @classmethod
    def read_from_env(cls, main_var_root: str):
        """ Creates VisioHTTPNode, contains main and mirror server from env
        :param main_var_root: name of environment variable for main server
        """
        mirror_var_root = main_var_root + '_MIRROR'
        try:
            return cls(main=VisioHTTPConfig.read_from_env(var_root=main_var_root),
                       mirror=VisioHTTPConfig.read_from_env(var_root=mirror_var_root)
                       )
        except EnvironmentError as e:
            _log.warning(f'{cls.__name__} cannot be read form environment variables.')
            raise e

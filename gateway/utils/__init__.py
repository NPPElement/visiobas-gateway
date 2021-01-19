from hashlib import md5
from os import environ


class VisioHTTPServerConfig:
    # That class allows to create only one instance for each server's params
    _instances = {}  # keeps instances references

    __slots__ = ('login', '__password_md5', 'host', 'port',
                 'bearer_token', 'user_id', 'auth_user_id'
                 )

    def __new__(cls, *args, **kwargs):
        _hash = hash(frozenset(kwargs.items()))
        if cls._instances.get(_hash, None) is None:
            cls._instances[_hash] = super().__new__(cls)
        return cls._instances[_hash]

    def __init__(self, *, login: str, password: str, host: str, port: int):
        self.login = login
        self.__password_md5 = md5(password.encode()).hexdigest()
        self.host = host
        self.port = port

        self.bearer_token = None
        self.user_id = None
        self.auth_user_id = None

    @classmethod
    def read_from_env(cls, var_name: str):
        try:
            return cls(login=environ[f'HTTP_{var_name}_LOGIN'],
                       password=environ[f'HTTP_{var_name}_PASSWORD'],
                       host=environ[f'HTTP_{var_name}_HOST'],
                       port=int(environ[f'HTTP_{var_name}_PORT'])
                       )
        except KeyError:
            raise EnvironmentError("Please ensure environment variables are set to: \n"
                                   f"'HTTP_{var_name}_HOST'\n"
                                   f"'HTTP_{var_name}_PORT'\n"
                                   f"'HTTP_{var_name}_LOGIN'\n"
                                   f"'HTTP_{var_name}_PASSWORD'"
                                   )

    def set_auth_data(self, bearer_token: str, user_id: int, auth_user_id: int) -> None:
        self.bearer_token = bearer_token
        self.user_id = user_id
        self.auth_user_id = auth_user_id

    @property
    def base_url(self) -> str:
        return 'http://' + ':'.join((self.host, str(self.port)))

    @property
    def auth_payload(self) -> dict[str, str]:
        data = {'login': self.login,
                'password': self.__password_md5
                }
        return data

    @property
    def auth_headers(self) -> dict[str, str]:
        if isinstance(self.bearer_token, str):
            headers = {'Authorization': f'Bearer {self.bearer_token}'
                       }
            return headers

    def __repr__(self) -> str:
        return f'VisioHTTPServerData({self.base_url}, login: {self.login})'


def read_cfg_from_env() -> dict:
    """
    :return: Config, read from environment variables
    """

    try:
        get_server_data = VisioHTTPServerConfig.read_from_env(var_name='GET')
        post_servers_data = []

        i = 0
        while True:
            try:
                var_name = f'POST_{i}'
                post_server_data = VisioHTTPServerConfig.read_from_env(var_name=var_name)
                post_servers_data.append(post_server_data)
                i += 1

            except EnvironmentError:
                break

        config = {
            'http': {
                'get_server_data': get_server_data,
                'post_servers_data': post_servers_data
            },
            'bacnet_verifier': {
                'http_enable': True if environ.get(
                    'HTTP_ENABLE').lower() == 'true' else False,
                'mqtt_enable': True if environ.get(
                    'MQTT_ENABLE').lower() == 'true' else False,
            },
            'bacnet': {
                'default_update_period': int(
                    environ.get('BACNET_DEFAULT_UPDATE_PERIOD', 10)),
                'interfaces': environ.get('BACNET_INTERFACES', '').split()
            },
            'modbus': {
                'default_update_period': int(
                    environ.get('MODBUS_DEFAULT_UPDATE_PERIOD', 10))
            }
        }
    except EnvironmentError:
        raise EnvironmentError(
            "Please ensure environment variables are set to: \n"
            "'HTTP_{server}_HOST'\n'HTTP_{server}_PORT'\n"
            "'HTTP_{server}_LOGIN'\n'HTTP_{server}_PASSWORD'\nfor each server.\n\n"

            "Also you can provide optional variables: \n"
            "'HTTP_PORT' by default = 8080\n"
            "'HTTP_ENABLE' by default = FALSE\n"
            "'MQTT_ENABLE' by default = FALSE\n"
            "'BACNET_DEFAULT_UPDATE_PERIOD' by default = 10\n"
            "'MODBUS_DEFAULT_UPDATE_PERIOD' by default = 10\n"
        )
    else:
        return config

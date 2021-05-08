from hashlib import md5
from typing import Optional, Union

from pydantic import BaseModel, Field, validator, HttpUrl
from yarl import URL


class AuthData(BaseModel):
    bearer_token: str = Field(..., alias='token')
    user_id: int = Field(...)
    auth_user_id: int = Field(...)


class HTTPServerConfig(BaseModel):
    """Represent parameters for Visio HTTP server.

    Singleton.

    # todo: add validator for URL?
    """
    login: str = Field(...)
    password: str = Field(...)
    url: HttpUrl = Field(...)  # in validation: HttpUlr -> URL

    auth_data: Optional[AuthData] = None
    is_authorized = False

    @validator('url')
    def cast_url(cls, v: HttpUrl) -> URL:
        return URL(v)

    @validator('password')
    def hash_password(cls, v: str) -> str:
        return md5(v.encode()).hexdigest()

    def __hash__(self) -> int:
        return hash((self.url, self.login))

    def __str__(self) -> str:
        _auth_status = 'Authorized' if self.is_authorized else 'Unauthorized'
        return f'[{_auth_status}:{self.url.host}]'

    def __repr__(self) -> str:
        return str(self)

    # @property
    # def is_authorized(self) -> bool:
    #     return self.is_authorized

    @property
    def auth_payload(self) -> dict[str, str]:
        return {'login': self.login, 'password': self.password}

    @property
    def auth_headers(self) -> dict[str, str]:
        if self.auth_data:
            return {'Authorization': f'Bearer {self.auth_data.bearer_token}'}

            # # That class allows to create only one instance for each server's params
            # _instances = {}  # keeps instances references

            # __slots__ = ('_login', '_password_md5', 'host', 'port',
            #              '_bearer_token', '_user_id', '_auth_user_id',
            #              'is_connected', 'is_authorized'
            #              )

            # def __new__(cls, *args, **kwargs):
            #     # Used kwargs because __init__ accept args by key
            #     _args_hash = hash((kwargs.get('login'),
            #                        kwargs.get('password'),
            #                        kwargs.get('host'),
            #                        kwargs.get('port')
            #                        ))
            #     if cls._instances.get(_args_hash) is None:
            #         cls._instances[_args_hash] = super().__new__(cls)
            #     return cls._instances[_args_hash]

            # def __init__(self, login: str, password: str, host: str, port: int):
            #     self.host = host
            #     self.port = port
            #
            #     self._login = login
            #     self._password_md5 = md5(password.encode()).hexdigest()
            #
            #     self._bearer_token = None
            #     self._user_id = None
            #     self._auth_user_id = None
            #
            #     # self.is_connected = True
            #     self.is_authorized = False

    def set_auth_data(self, **kwargs) -> None:
        self.auth_data = AuthData(**kwargs)
        self.is_authorized = True

    def clear_auth_data(self) -> None:
        self.auth_data = None
        self.is_authorized = False

    # @classmethod
    # def from_dict(cls, cfg: dict):
    #     """Create HTTP config for server from dict."""
    #     return cls(login=cfg['login'],
    #                password=cfg['password'],
    #                host=cfg['host'],
    #                port=cfg.get('port', 8080)
    #                )

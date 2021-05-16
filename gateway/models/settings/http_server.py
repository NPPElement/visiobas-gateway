from hashlib import md5
from typing import Optional

from pydantic import Field, BaseModel, validator, AnyHttpUrl


class AuthData(BaseModel):
    bearer_token: str = Field(..., alias='token')
    user_id: int = Field(...)
    auth_user_id: int = Field(...)


class HTTPServerConfig(BaseModel):
    urls: list[AnyHttpUrl] = Field(...)
    current = 0
    auth_data: Optional[AuthData] = None

    @validator('urls')
    def hash_passwords(cls, v: list[AnyHttpUrl]) -> list[AnyHttpUrl]:
        for url in v:
            if not url.password:
                raise ValueError('Password expected')
            if not url.user:
                raise ValueError('User expected')
            if not url.port:
                raise ValueError('Port expected')
        return v

    @property
    def urls_len(self) -> int:
        return len(self.urls)

    @property
    def _current_url(self) -> AnyHttpUrl:
        return self.urls[self.current]  # current url

    @property
    def current_url(self) -> str:
        url_ = self._current_url
        return url_.scheme + '://' + url_.host + ':' + url_.port

    @property
    def is_authorized(self) -> bool:
        return bool(self.auth_data)

    @property
    def auth_payload(self) -> dict[str, str]:
        return {'login': self._current_url.user,
                'password': self._get_hash(self._current_url.password)}

    @property
    def auth_headers(self) -> Optional[dict[str, str]]:
        if self.auth_data:
            return {'Authorization': f'Bearer {self.auth_data.bearer_token}'}

    def __str__(self) -> str:
        return str(self._current_url.host)

    def __repr__(self) -> str:
        return str(self)

    def set_auth_data(self, **kwargs) -> None:
        self.auth_data = AuthData(**kwargs)

    def clear_auth_data(self) -> None:
        self.auth_data = None

    def switch_server(self) -> bool:
        """Switches communication from current to next, if it exist.

        Uses in change server when current unavailable.

        Returns:
            True: If url switched to unused
            False: If url switched to already used.
        """
        self.current = self.current + 1 if self.current < self.urls_len - 1 else 0
        return True if self.current else False

    @staticmethod
    def _get_hash(password: str) -> str:
        return md5(password.encode()).hexdigest()

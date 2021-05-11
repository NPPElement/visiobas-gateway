from hashlib import md5
from typing import Optional

from pydantic import Field, BaseModel, HttpUrl, validator, AnyHttpUrl, BaseSettings


class AuthData(BaseModel):
    bearer_token: str = Field(..., alias='token')
    user_id: int = Field(...)
    auth_user_id: int = Field(...)


class HTTPServerConfig(BaseModel):
    urls: list[AnyHttpUrl] = Field(...)
    current = 0
    auth_data: Optional[AuthData] = None

    @property
    def urls_len(self) -> int:
        return len(self.urls)

    @property
    def current_url(self) -> AnyHttpUrl:
        return self.urls[self.current]

    @property
    def is_authorized(self) -> bool:
        return bool(self.auth_data)

    @property
    def auth_payload(self) -> dict[str, str]:
        return {'login': self.current_url.user,
                'password': self.current_url.password}

    @property
    def auth_headers(self) -> Optional[dict[str, str]]:
        if self.auth_data:
            return {'Authorization': f'Bearer {self.auth_data.bearer_token}'}

    def __str__(self) -> str:
        return str(self.current_url.host)

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

    @validator('urls')
    def hash_passwords(cls, v: list[HttpUrl]) -> list[HttpUrl]:
        for url in v:
            url.password = md5(url.password.encode()).hexdigest()
        return v

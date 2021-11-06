from hashlib import md5
from typing import Any, Optional

from pydantic import AnyHttpUrl, BaseModel, Field, SecretStr, validator


class AuthData(BaseModel):
    """Auth settings of `HTTPServerConfig`."""

    bearer_token: SecretStr = Field(..., alias="token")
    user_id: int = Field(...)
    auth_user_id: int = Field(...)


class HTTPServerConfig(BaseModel):
    """Config of HTTP Server for GET or POST data."""

    urls: list[AnyHttpUrl] = Field(..., min_items=1)

    auth_data: Optional[AuthData] = None
    current_url: AnyHttpUrl = None  # type: ignore

    @validator("urls")
    def check_required(cls, value: list[AnyHttpUrl]) -> list[AnyHttpUrl]:
        # pylint: disable=no-self-argument
        for url in value:
            if url.password:
                url.password = cls._get_hash(password=url.password)
            else:
                raise ValueError("Password required.")

            if not url.user:
                raise ValueError("User required.")
            if not url.port:
                raise ValueError("Port required.")
        return value

    @staticmethod
    def get_url_str(url: AnyHttpUrl) -> str:
        return f"{url.scheme}://{url.host}:{url.port}"

    @property
    def auth_payload(self) -> dict[str, str]:
        return {
            "login": self.current_url.user,  # type: ignore
            "password": self.current_url.password,  # type: ignore
        }

    @property
    def auth_headers(self) -> dict[str, str]:
        if self.auth_data:
            return {
                "Authorization": f"Bearer {self.auth_data.bearer_token.get_secret_value()}"
            }
        return {}

    # def __str__(self) -> str:
    #     return ":".join((self.current_url.host, self.current_url.port))  # type: ignore
    #
    # def __repr__(self) -> str:
    #     return str(self)

    def set_auth_data(self, **kwargs: Any) -> None:
        self.auth_data = AuthData(**kwargs)

    def clear_auth_data(self) -> None:
        self.auth_data = None

    @staticmethod
    def _get_hash(password: str) -> str:
        return md5(password.encode()).hexdigest()

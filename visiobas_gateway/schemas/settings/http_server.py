from hashlib import md5
from typing import Any, Optional, Union

from pydantic import AnyHttpUrl, BaseModel, Field, SecretStr, validator

from ..secret_url import SecretUrl, cast_to_secret_urls


class AuthData(BaseModel):
    """Auth settings of `HTTPServerConfig`."""

    bearer_token: SecretStr = Field(..., alias="token")
    user_id: int = Field(...)
    auth_user_id: int = Field(...)


class HttpServerConfig(BaseModel):
    """Config of HTTP Server for GET or POST data."""

    urls: list[Union[AnyHttpUrl, SecretUrl]] = Field(..., min_items=1)  #

    _cast_to_secret_urls = validator("urls", allow_reuse=True)(cast_to_secret_urls)

    auth_data: Optional[AuthData] = None
    current_url: SecretUrl = None

    @staticmethod
    def get_url_str(url: SecretUrl) -> str:
        return f"{url.scheme}://{url.host}:{url.port}"

    @property
    def auth_payload(self) -> dict[str, str]:
        return {
            "login": self.current_url.user.get_secret_value(),
            "password": self.current_url.password.get_secret_value(),
        }

    @property
    def auth_headers(self) -> dict[str, str]:
        if self.auth_data:
            return {
                "Authorization": f"Bearer {self.auth_data.bearer_token.get_secret_value()}"
            }
        return {}

    def set_auth_data(self, **kwargs: Any) -> None:
        self.auth_data = AuthData(**kwargs)

    def clear_auth_data(self) -> None:
        self.auth_data = None

    @staticmethod
    def _get_hash(password: SecretStr) -> str:
        return md5(password.get_secret_value().encode()).hexdigest()

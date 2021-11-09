from pydantic import AnyUrl, BaseModel, Field, SecretStr


class SecretUrl(BaseModel):
    """Simple container for credentials with hidden sensitive data.

    `scheme`, `user`, `password`, `host`, `port` are required.
    """

    scheme: str = Field(...)
    user: SecretStr = Field(...)
    password: SecretStr = Field(...)
    host: str = Field(...)
    port: int = Field(...)


def cast_to_secret_url(v: AnyUrl) -> SecretUrl:
    return SecretUrl(
        scheme=v.scheme, user=v.user, password=v.password, host=v.host, port=v.port
    )


def cast_to_secret_urls(v: list[AnyUrl]) -> list[SecretUrl]:
    return [
        SecretUrl(
            scheme=url.scheme,
            user=url.user,
            password=url.password,
            host=url.host,
            port=url.port,
        )
        for url in v
    ]

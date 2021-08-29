from pydantic import AnyHttpUrl, BaseSettings, Field


class ApiSettings(BaseSettings):
    url: AnyHttpUrl = Field(default="http://0.0.0.0:7070", description="Url to run API.")
    priority: int = Field(default=11, description="Priority to write through gateway API.")

    class Config:
        env_prefix = "GTW_API_"
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def host(self) -> str:
        return self.url.host

    @property
    def port(self) -> int:
        return int(self.url.port)

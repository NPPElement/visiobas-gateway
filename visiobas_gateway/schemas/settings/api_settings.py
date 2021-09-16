from pydantic import AnyHttpUrl, BaseSettings, Field

from ..bacnet.priority import Priority


class ApiSettings(BaseSettings):
    """Settings of API application."""

    HOST: AnyHttpUrl = Field(
        default="http://0.0.0.0", description="Host to server API (without port)."
    )
    PORT: int = Field(default=7070, ge=1024, le=65535, description="Port to serve API.")
    PRIORITY: Priority = Field(
        default=Priority.CONTROL_LOOP_FLICK_WARN,
        description="BACnet " "priority of write through API.",
    )

    class Config:  # pylint: disable=missing-class-docstring
        env_prefix = "GTW_API_"
        env_file = ".env"
        env_file_encoding = "utf-8"


api_settings = ApiSettings()

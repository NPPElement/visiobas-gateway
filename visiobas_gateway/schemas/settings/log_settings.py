from pathlib import Path

from pydantic import BaseSettings, Field

from visiobas_gateway import BASE_DIR


class LogSettings(BaseSettings):
    """Settings of logging."""

    level: str = Field(default="DEBUG")
    file_level: str = Field(default="DEBUG")
    file_size: int = Field(default=50, description="Number of MB for log files.")
    format: str = Field(
        default="%(levelname)-8s [%(asctime)s] "
        "%(name)s.%(funcName)s(%(lineno)d): %(message)s"
    )  # [%(threadName)s]
    disable_loggers: list[str] = Field(
        default_factory=list, description="List of logger names to disable."
    )
    log_dir: Path = Field(default=BASE_DIR.parent / ".gtw_logs")

    # @validator("disable_loggers", pre=True)
    # def spit_names(cls, value: list[str]) -> list[str]:
    #     # pylint: disable=no-self-argument
    #     return value.split()

    class Config:  # pylint: disable=missing-class-docstring
        env_prefix = "GTW_LOG_"
        env_file = ".env"
        env_file_encoding = "utf-8"


log_settings = LogSettings()

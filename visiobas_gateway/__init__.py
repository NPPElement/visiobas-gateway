"""VisioBAS Gateway."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "config"
ENV_PATH = CONFIG_DIR / ".env"

__all__ = [
    "BASE_DIR",
    "ENV_PATH",
]

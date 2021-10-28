"""VisioBAS Gateway."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
GATEWAY_VERSION = "3.5.1"

__all__ = [
    "BASE_DIR",
    "GATEWAY_VERSION",
]

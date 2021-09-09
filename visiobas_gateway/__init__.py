"""VisioBAS Gateway."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "docs"

__all__ = [
    "BASE_DIR",
    "DOCS_DIR",
]

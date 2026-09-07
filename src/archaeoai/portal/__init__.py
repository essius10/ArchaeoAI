"""Local-only professional portal demonstration."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def create_app(database_path: Path | None = None) -> Any:
    """Load the optional FastAPI application factory only when requested."""
    from archaeoai.portal.app import create_app as factory

    return factory(database_path)


__all__ = ["create_app"]

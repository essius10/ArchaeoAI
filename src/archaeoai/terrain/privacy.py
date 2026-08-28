"""Privacy boundary for coordinate-bearing E001 terrain artifacts."""

from __future__ import annotations

import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from archaeoai.paths import ensure_within_project

PRIVATE_RELATIVE_ROOT = Path("data/private")
FORBIDDEN_TRACKED_FIELDS = frozenset(
    {
        "easting",
        "northing",
        "ngr",
        "latitude",
        "longitude",
        "geometry",
        "polygon",
        "bbox",
        "bounds",
        "centre",
        "center",
    }
)


def ensure_private_output(project_root: Path, candidate: str | Path) -> Path:
    root = project_root.resolve()
    private_root = (root / PRIVATE_RELATIVE_ROOT).resolve()
    resolved = ensure_within_project(root, Path(candidate), field_name="private output")
    try:
        resolved.relative_to(private_root)
    except ValueError as exc:
        raise ValueError(f"coordinate-bearing output must remain under {private_root}") from exc
    return resolved


def verify_git_ignored(project_root: Path, candidate: str | Path) -> None:
    root = project_root.resolve()
    resolved = ensure_private_output(root, candidate)
    relative = resolved.relative_to(root)
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "--", str(relative)],
        cwd=root,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(f"private output is not ignored by Git: {relative}")


def assert_coordinate_safe_mapping(mapping: Mapping[str, Any]) -> None:
    """Reject exact-location field names recursively before tracked serialization."""
    for key, value in mapping.items():
        normalized = key.casefold().replace("-", "_").strip()
        if normalized in FORBIDDEN_TRACKED_FIELDS:
            raise ValueError(f"coordinate-bearing field cannot be tracked: {key}")
        if isinstance(value, Mapping):
            assert_coordinate_safe_mapping(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    assert_coordinate_safe_mapping(item)

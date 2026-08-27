"""Project-root discovery and safe repository-relative path handling."""

from pathlib import Path


class ProjectPathError(ValueError):
    """Raised when a configured path is invalid or leaves the project root."""


def find_project_root(start: Path | None = None) -> Path:
    """Find the nearest parent containing ``pyproject.toml``."""
    current = (start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate

    raise ProjectPathError(f"Could not find pyproject.toml from {current}")


def ensure_within_project(project_root: Path, candidate: Path, *, field_name: str) -> Path:
    """Resolve ``candidate`` and require it to remain inside ``project_root``."""
    root = project_root.resolve()
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ProjectPathError(
            f"{field_name} must remain inside project root: {candidate}"
        ) from exc
    return resolved


def resolve_project_path(project_root: Path, raw_path: str, *, field_name: str) -> Path:
    """Resolve a non-empty, repository-relative configuration path safely."""
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ProjectPathError(f"{field_name} must be a non-empty relative path")

    configured = Path(raw_path)
    if configured.is_absolute():
        raise ProjectPathError(f"{field_name} must be relative to the project root")

    return ensure_within_project(
        project_root,
        project_root / configured,
        field_name=field_name,
    )

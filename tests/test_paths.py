from pathlib import Path

import pytest

from archaeoai.paths import ProjectPathError, find_project_root, resolve_project_path


def test_resolve_project_path_accepts_repository_relative_path(tmp_path: Path) -> None:
    resolved = resolve_project_path(tmp_path, "data/raw", field_name="data_root")

    assert resolved == tmp_path / "data" / "raw"


def test_resolve_project_path_rejects_parent_escape(tmp_path: Path) -> None:
    with pytest.raises(ProjectPathError, match="inside project root"):
        resolve_project_path(tmp_path, "../outside", field_name="data_root")


def test_resolve_project_path_rejects_absolute_path(tmp_path: Path) -> None:
    absolute_path = str(Path(tmp_path.anchor) / "outside")

    with pytest.raises(ProjectPathError, match="must be relative"):
        resolve_project_path(tmp_path, absolute_path, field_name="data_root")


def test_find_project_root_from_nested_directory() -> None:
    root = find_project_root(Path(__file__))

    assert (root / "pyproject.toml").is_file()

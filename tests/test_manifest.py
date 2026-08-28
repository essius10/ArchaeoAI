from pathlib import Path

import pytest

from archaeoai.data.manifest import ManifestError, load_dataset_manifest

VALID_ACQUIRED_MANIFEST = """
[dataset]
id = "TEST_DATASET_001"
name = "Test dataset"
description = "Synthetic test metadata; no real dataset."
status = "acquired"
sensitivity = "restricted"

[source]
provider = "Test provider"
url = "https://example.invalid/test-dataset"
license = "Test-only license placeholder"
attribution = "Test attribution"
edition = "Test edition"
service_url = "https://example.invalid/test-wcs"
access_date = 2026-08-27

[spatial]
crs = "EPSG:27700"
vertical_datum = "Synthetic datum"
resolution_m = 1.0
geographic_area = "Synthetic test area"
acquisition_date = 2026-01-01

[file]
expected_local_path = "data/raw/test/elevation.tif"
sha256 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
checksum_scope = "single synthetic file"
"""


def _write_manifest(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "manifest.toml"
    path.write_text(content, encoding="utf-8")
    return path


def test_loads_fictional_example_manifest() -> None:
    root = Path(__file__).resolve().parents[1]

    manifest = load_dataset_manifest(root / "data" / "manifests" / "example-dataset.toml")

    assert manifest.dataset_id == "EXAMPLE_FICTIONAL_DTM"
    assert manifest.status == "template"
    assert manifest.sensitivity == "public"
    assert manifest.source.url.startswith("https://example.invalid/")
    assert manifest.source.access_date is None
    assert manifest.file.sha256 is None


def test_loads_valid_acquired_manifest(tmp_path: Path) -> None:
    manifest = load_dataset_manifest(
        _write_manifest(tmp_path, VALID_ACQUIRED_MANIFEST),
        project_root=tmp_path,
    )

    assert manifest.status == "acquired"
    assert manifest.file.sha256 == "a" * 64
    assert manifest.file.expected_local_path == tmp_path / "data" / "raw" / "test" / "elevation.tif"
    assert manifest.source.attribution == "Test attribution"
    assert manifest.source.service_url == "https://example.invalid/test-wcs"
    assert manifest.spatial.vertical_datum == "Synthetic datum"
    assert manifest.file.checksum_scope == "single synthetic file"


def test_loads_consistent_optional_dataset_freeze_counts(tmp_path: Path) -> None:
    content = VALID_ACQUIRED_MANIFEST.replace(
        'sensitivity = "restricted"',
        'sensitivity = "restricted"\nrequested_records = 3\nacquired_records = 2\n'
        'rejected_records = 1\nacquisition_version = "test-acquire-v1"\n'
        'processing_version = "test-process-v1"',
    )

    manifest = load_dataset_manifest(_write_manifest(tmp_path, content), project_root=tmp_path)

    assert manifest.requested_records == 3
    assert manifest.acquired_records == 2
    assert manifest.rejected_records == 1
    assert manifest.acquisition_version == "test-acquire-v1"
    assert manifest.processing_version == "test-process-v1"


def test_rejects_inconsistent_dataset_freeze_counts(tmp_path: Path) -> None:
    content = VALID_ACQUIRED_MANIFEST.replace(
        'sensitivity = "restricted"',
        'sensitivity = "restricted"\nrequested_records = 3\nacquired_records = 3\n'
        "rejected_records = 1",
    )

    with pytest.raises(ManifestError, match="must equal requested"):
        load_dataset_manifest(_write_manifest(tmp_path, content), project_root=tmp_path)


def test_rejects_invalid_checksum_syntax(tmp_path: Path) -> None:
    content = VALID_ACQUIRED_MANIFEST.replace("a" * 64, "not-a-sha256")

    with pytest.raises(ManifestError, match="64 hexadecimal"):
        load_dataset_manifest(_write_manifest(tmp_path, content), project_root=tmp_path)


def test_rejects_unknown_sensitivity_classification(tmp_path: Path) -> None:
    content = VALID_ACQUIRED_MANIFEST.replace(
        'sensitivity = "restricted"', 'sensitivity = "secret"'
    )

    with pytest.raises(ManifestError, match="sensitivity classification"):
        load_dataset_manifest(_write_manifest(tmp_path, content), project_root=tmp_path)


def test_rejects_acquired_manifest_without_checksum(tmp_path: Path) -> None:
    content = VALID_ACQUIRED_MANIFEST.replace(f'sha256 = "{"a" * 64}"', "")

    with pytest.raises(ManifestError, match="require access_date and sha256"):
        load_dataset_manifest(_write_manifest(tmp_path, content), project_root=tmp_path)


def test_rejects_manifest_path_escape(tmp_path: Path) -> None:
    content = VALID_ACQUIRED_MANIFEST.replace(
        'expected_local_path = "data/raw/test/elevation.tif"',
        'expected_local_path = "../outside.tif"',
    )

    with pytest.raises(ValueError, match="inside project root"):
        load_dataset_manifest(_write_manifest(tmp_path, content), project_root=tmp_path)


def test_rejects_malformed_manifest_toml(tmp_path: Path) -> None:
    path = _write_manifest(tmp_path, "[dataset\nid = 'BROKEN'")

    with pytest.raises(ManifestError, match="Could not load dataset manifest"):
        load_dataset_manifest(path, project_root=tmp_path)

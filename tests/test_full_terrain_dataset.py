from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from archaeoai.terrain.acquisition import PrivateSiteLocation
from archaeoai.terrain.full_dataset import (
    REPRESENTATION_NAMES,
    inspect_cached_artifacts,
    validate_representations,
    write_processed_archive,
)
from archaeoai.terrain.representations import terrain_representations


def _location() -> PrivateSiteLocation:
    return PrivateSiteLocation(
        list_entry=1,
        easting=64,
        northing=64,
        geographic_group_id="G1",
        terrain_year="2021",
        source_resolution_m="1",
        survey_program="synthetic",
    )


def _write_raster(path: Path, offset: float = 0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    y, x = np.mgrid[:128, :128]
    values = (offset + x * 0.2 + y * 0.1).astype(np.float32)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=128,
        height=128,
        count=1,
        dtype="float32",
        crs="EPSG:27700",
        transform=from_origin(0, 128, 1, 1),
        nodata=-9999,
    ) as dataset:
        dataset.write(values, 1)


def test_representation_qa_requires_complete_deterministic_frozen_set() -> None:
    values = np.arange(128 * 128, dtype=np.float32).reshape(128, 128)
    mask = np.zeros_like(values, dtype=bool)
    representations = terrain_representations(values, resolution_m=1, mask=mask)

    passed = validate_representations(representations, source_mask=mask)
    assert passed.passed
    assert len(passed.digest) == 64

    incomplete = {name: representations[name] for name in REPRESENTATION_NAMES[:-1]}
    assert validate_representations(incomplete, source_mask=mask).reasons == (
        "representation_set_incomplete",
    )

    altered = {name: values.copy() for name, values in representations.items()}
    altered["hillshade_315_45"][0, 0] = 2
    failed = validate_representations(
        altered, source_mask=mask, deterministic_reference=representations
    )
    assert "hillshade_315_45:range" in failed.reasons
    assert "hillshade_315_45:deterministic_mismatch" in failed.reasons


def test_cache_resume_skip_checksum_and_corruption_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw_path = tmp_path / "data/private/e001/terrain/raw/sample.tif"
    processed_path = tmp_path / "data/private/e001/terrain/processed/sample.npz"
    _write_raster(raw_path)
    monkeypatch.setattr("archaeoai.terrain.full_dataset.verify_git_ignored", lambda *_args: None)

    missing = inspect_cached_artifacts(
        raw_path=raw_path,
        processed_path=processed_path,
        location=_location(),
    )
    assert missing.status == "processed_missing"
    assert missing.patch is not None
    assert missing.representations is not None

    write_processed_archive(
        processed_path,
        patch=missing.patch,
        representations=missing.representations,
        project_root=tmp_path,
    )
    valid = inspect_cached_artifacts(
        raw_path=raw_path,
        processed_path=processed_path,
        location=_location(),
        expected_raw_sha256=missing.raw_sha256,
    )
    assert valid.status == "valid"
    assert len(valid.processed_sha256) == 64

    processed_path.write_bytes(b"corrupt archive")
    corrupted = inspect_cached_artifacts(
        raw_path=raw_path,
        processed_path=processed_path,
        location=_location(),
        expected_raw_sha256=missing.raw_sha256,
    )
    assert corrupted.status == "processed_invalid"

    _write_raster(raw_path, offset=100)
    checksum_mismatch = inspect_cached_artifacts(
        raw_path=raw_path,
        processed_path=processed_path,
        location=_location(),
        expected_raw_sha256=missing.raw_sha256,
    )
    assert checksum_mismatch.status == "raw_invalid"
    assert checksum_mismatch.reasons == ("raw_checksum_mismatch",)


def test_partial_cache_file_is_never_accepted_as_complete(tmp_path: Path) -> None:
    raw_path = tmp_path / "data/private/e001/terrain/raw/sample.tif"
    raw_path.parent.mkdir(parents=True)
    raw_path.with_name("sample.partial.tif").write_bytes(b"II*\x00partial")

    inspection = inspect_cached_artifacts(
        raw_path=raw_path,
        processed_path=tmp_path / "data/private/e001/terrain/processed/sample.npz",
        location=_location(),
    )

    assert inspection.status == "raw_missing"

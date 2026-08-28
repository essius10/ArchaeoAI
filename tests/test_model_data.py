import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from archaeoai.model_data import (
    DevelopmentDataLoader,
    FinalTestAccessError,
    configuration_hash,
    mean_pool_4x4,
    validate_frozen_primary_config,
)
from archaeoai.terrain.full_dataset import terrain_content_digest


def test_mean_pool_4x4_has_expected_shape_values_and_finite_nodata_fallback() -> None:
    values = np.arange(128 * 128, dtype=np.float32).reshape(128, 128)
    values[:4, :4] = np.nan
    pooled = mean_pool_4x4(values)

    assert pooled.shape == (1024,)
    assert pooled.dtype == np.float32
    assert pooled[0] == 0
    assert pooled[1] == pytest.approx(values[:4, 4:8].mean())
    assert np.isfinite(pooled).all()


def test_mean_pool_rejects_non_frozen_shape() -> None:
    with pytest.raises(ValueError, match="128x128"):
        mean_pool_4x4(np.zeros((64, 64), dtype=np.float32))


def _write_archive(path: Path, value: float) -> str:
    elevation = np.full((128, 128), value, dtype=np.float32)
    mask = np.zeros((128, 128), dtype=bool)
    layers = {
        "elevation_normalized": elevation.copy(),
        "slope_degrees": elevation.copy(),
        "hillshade_315_45": elevation.copy(),
        "local_relief_r16m": elevation.copy(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, elevation=elevation, mask=mask, **layers)
    return terrain_content_digest(elevation, mask)


def _synthetic_project(root: Path) -> None:
    output = root / "outputs/dataset"
    output.mkdir(parents=True)
    fields = [
        "sample_id",
        "class_label",
        "observation_group_id",
        "overlap_component_id",
        "geographic_block_id",
        "survey_year",
        "provenance_id",
        "source_resolution_m",
        "patch_size_m",
        "processing_version",
        "qa_status",
        "sampling_stratum",
        "patch_sha256",
        "split_random",
        "split_geographic",
    ]
    specifications = [
        ("P-train", "positive_bowl_barrow", "train", 1.0),
        ("B-train", "unlabelled_background", "train", 2.0),
        ("P-development", "positive_bowl_barrow", "development", 3.0),
        ("B-development", "unlabelled_background", "development", 4.0),
        ("P-final", "positive_bowl_barrow", "final_test", 5.0),
        ("B-final", "unlabelled_background", "final_test", 6.0),
    ]
    rows = []
    for sample_id, label, partition, value in specifications:
        private_subdir = (
            "terrain/processed" if label == "positive_bowl_barrow" else ("backgrounds/processed")
        )
        digest = _write_archive(
            root / "data/private/e001" / private_subdir / f"{sample_id}.npz", value
        )
        rows.append(
            {
                "sample_id": sample_id,
                "class_label": label,
                "observation_group_id": sample_id,
                "overlap_component_id": "",
                "geographic_block_id": "BLOCK",
                "survey_year": "2020",
                "provenance_id": "PROV",
                "source_resolution_m": "1.0",
                "patch_size_m": "128",
                "processing_version": "test",
                "qa_status": "pass",
                "sampling_stratum": "test",
                "patch_sha256": digest,
                "split_random": partition,
                "split_geographic": partition,
            }
        )
    with (output / "e001_modelling_index.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda item: item["sample_id"]):
        digest.update(f"{row['sample_id']}:{row['split_geographic']}\n".encode())
    (output / "e001_geographic_split_manifest.json").write_text(
        json.dumps({"frozen": True, "assignment_sha256": digest.hexdigest()}),
        encoding="utf-8",
    )


def test_loader_uses_index_labels_checks_integrity_and_blocks_final_test(tmp_path: Path) -> None:
    _synthetic_project(tmp_path)
    loader = DevelopmentDataLoader(tmp_path)

    train = loader.load_partition("train", "normalized_elevation")
    development = loader.load_partition("development", "all_four")
    assert train.features.shape == (2, 1024)
    assert development.features.shape == (2, 4096)
    assert train.labels.tolist() == [0, 1]
    assert all(row.class_label is None for row in loader.rows if row.partition == "final_test")
    with pytest.raises(FinalTestAccessError):
        loader.load_partition("final_test", "slope")
    with pytest.raises(FinalTestAccessError):
        loader.allowed_metadata_rows("final_test")


def test_loader_rejects_patch_content_mismatch(tmp_path: Path) -> None:
    _synthetic_project(tmp_path)
    loader = DevelopmentDataLoader(tmp_path)
    archive = tmp_path / "data/private/e001/terrain/processed/P-train.npz"
    _write_archive(archive, 99.0)

    with pytest.raises(ValueError, match="checksum mismatch"):
        loader.load_partition("train", "slope")


def test_frozen_configuration_hash_guard(tmp_path: Path) -> None:
    payload: dict[str, object] = {"frozen": True, "model": "logistic_regression"}
    payload["config_sha256"] = configuration_hash(payload)
    path = tmp_path / "primary.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert validate_frozen_primary_config(path)["model"] == "logistic_regression"

    payload["model"] = "random_forest"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        validate_frozen_primary_config(path)

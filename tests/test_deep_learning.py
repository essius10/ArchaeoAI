import csv
import hashlib
import io
from dataclasses import fields
from pathlib import Path

import numpy as np
import pytest
import torch

from archaeoai.deep_learning import (
    CNN_INPUT_SHAPE,
    EXPECTED_FOLD_SHA256,
    CNNRecord,
    CompactTerrainCNN,
    E001TerrainDataset,
    build_fold_partitions,
    configure_determinism,
    fit_training_normalization,
    private_checkpoint_payload,
    read_cnn_records,
    read_fold_assignments,
    trainable_parameter_count,
)
from archaeoai.terrain.full_dataset import REPRESENTATION_NAMES, terrain_content_digest

ROOT = Path(__file__).resolve().parents[1]


def _write_synthetic_case(root: Path) -> tuple[tuple[CNNRecord, ...], Path]:
    index_path = root / "index.csv"
    private_root = root / "private"
    headers = (
        "sample_id",
        "class_label",
        "geographic_block_id",
        "observation_group_id",
        "overlap_component_id",
        "patch_sha256",
        "qa_status",
    )
    rows = []
    for index, (sample_id, label, subdirectory) in enumerate(
        (
            ("opaque-positive", "positive_bowl_barrow", "terrain/processed"),
            ("opaque-background", "unlabelled_background", "backgrounds/processed"),
        )
    ):
        grid = np.arange(128 * 128, dtype=np.float32).reshape(128, 128) + index
        elevation = grid + 100
        mask = np.zeros((128, 128), dtype=bool)
        representations = {
            name: grid / (channel + 1) + channel
            for channel, name in enumerate(REPRESENTATION_NAMES)
        }
        archive_path = private_root / subdirectory / f"{sample_id}.npz"
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(archive_path, elevation=elevation, mask=mask, **representations)
        rows.append(
            {
                "sample_id": sample_id,
                "class_label": label,
                "geographic_block_id": f"group-{index}",
                "observation_group_id": f"pair-{index}",
                "overlap_component_id": "",
                "patch_sha256": terrain_content_digest(elevation, mask),
                "qa_status": "pass",
            }
        )
    with index_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    return read_cnn_records(index_path, enforce_e001_counts=False), private_root


def test_cnn_loader_returns_only_four_channel_image_and_index_label(tmp_path: Path) -> None:
    records, private_root = _write_synthetic_case(tmp_path)
    dataset = E001TerrainDataset(records, private_root=private_root, role="internal_train")
    positive_image, positive_label = dataset[0]
    background_image, background_label = dataset[1]
    assert tuple(positive_image.shape) == CNN_INPUT_SHAPE
    assert tuple(background_image.shape) == CNN_INPUT_SHAPE
    assert positive_label.item() == 1.0
    assert background_label.item() == 0.0


def test_cnn_record_schema_has_no_coordinate_or_confound_features() -> None:
    names = {field.name for field in fields(CNNRecord)}
    assert names.isdisjoint(
        {
            "easting",
            "northing",
            "coordinates",
            "provenance_id",
            "survey_year",
            "source_resolution_m",
            "filename",
            "path",
        }
    )


def test_compact_cnn_shape_and_parameter_budget() -> None:
    model = CompactTerrainCNN()
    assert trainable_parameter_count(model) == 59145
    assert 50_000 <= trainable_parameter_count(model) <= 500_000
    assert model(torch.zeros((2, *CNN_INPUT_SHAPE))).shape == (2,)


def test_frozen_geographic_assignments_are_reused_exactly() -> None:
    assignments = read_fold_assignments(ROOT / "outputs/robustness/e001_geographic_fold_groups.csv")
    assert len(assignments) == 23
    assert EXPECTED_FOLD_SHA256 == (
        "825eb1088a53f764f991bf6bb22f2c9fe6eeb868916a5abab92012eed85d90ab"
    )


def test_internal_validation_never_uses_held_out_fold() -> None:
    records = read_cnn_records(ROOT / "outputs/dataset/e001_modelling_index.csv")
    assignments = read_fold_assignments(ROOT / "outputs/robustness/e001_geographic_fold_groups.csv")
    for held_out_fold in range(5):
        partitions = build_fold_partitions(records, assignments, held_out_fold=held_out_fold)
        assert all(
            assignments[record.geographic_block_id] != held_out_fold
            for record in partitions.internal_validation
        )
        assert all(
            assignments[record.geographic_block_id] == held_out_fold
            for record in partitions.held_out
        )


def test_matched_and_overlap_units_are_preserved_across_cnn_partitions() -> None:
    records = read_cnn_records(ROOT / "outputs/dataset/e001_modelling_index.csv")
    assignments = read_fold_assignments(ROOT / "outputs/robustness/e001_geographic_fold_groups.csv")
    partitions = build_fold_partitions(records, assignments, held_out_fold=0)
    seen: dict[str, set[str]] = {}
    for name, partition in (
        ("train", partitions.internal_train),
        ("validation", partitions.internal_validation),
        ("held", partitions.held_out),
    ):
        for record in partition:
            seen.setdefault(record.related_unit_id, set()).add(name)
    assert all(len(parts) == 1 for parts in seen.values())


def test_normalization_is_fitted_on_internal_training_only(tmp_path: Path) -> None:
    records, private_root = _write_synthetic_case(tmp_path)
    training = E001TerrainDataset(records, private_root=private_root, role="internal_train")
    normalization = fit_training_normalization(training)
    assert normalization.fitted_on == "internal_train"
    validation = E001TerrainDataset(records, private_root=private_root, role="internal_validation")
    with pytest.raises(ValueError, match="only on internal training"):
        fit_training_normalization(validation)


def test_deterministic_cpu_inference() -> None:
    configure_determinism(20260829)
    first = CompactTerrainCNN().eval()
    inputs = torch.linspace(0, 1, 4 * 128 * 128).reshape(1, 4, 128, 128)
    with torch.inference_mode():
        first_output = first(inputs)
    configure_determinism(20260829)
    second = CompactTerrainCNN().eval()
    with torch.inference_mode():
        second_output = second(inputs)
    assert torch.equal(first_output, second_output)


def test_checkpoint_payload_is_weights_only_and_coordinate_safe() -> None:
    payload = private_checkpoint_payload(CompactTerrainCNN(), protocol_sha256="a" * 64, epoch=0)
    assert set(payload) == {"state_dict", "protocol_sha256", "epoch"}
    forbidden = "coordinate easting northing sample_id filename path provenance survey_year bng"
    keys = " ".join(payload["state_dict"])
    assert not any(term in keys.casefold() for term in forbidden.split())
    buffer = io.BytesIO()
    torch.save(payload, buffer)
    assert buffer.tell() > 0


@pytest.mark.parametrize("extension", ("pt", "pth"))
def test_torch_checkpoints_are_ignored_by_git(extension: str, tmp_path: Path) -> None:
    del tmp_path
    import subprocess

    result = subprocess.run(
        ["git", "check-ignore", f"private-checkpoint.{extension}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0


@pytest.mark.parametrize(
    ("relative_path", "expected"),
    (
        (
            "outputs/modelling/e001_final_results.csv",
            "28b7503965ea75143616f5e726890b842030a20be8c283e2e9a7dd3c540e39a6",
        ),
        (
            "outputs/modelling/e001_random_vs_geographic.json",
            "6d6d8cf9ebca15d7cf28c99e9d05d9b94b5837695aaf29a973c80d708aad9055",
        ),
        (
            "outputs/modelling/e001_final_model_audit.json",
            "ad1204c002b6eb591b9ccf8cfdc89021ffcc6f8b709b30aae6fefd0ec9e891c2",
        ),
        (
            "outputs/robustness/e001_robustness_summary.json",
            "6ebf881562458110562e7181824c677acf7ecfa7edc673152e96bf1a7c319591",
        ),
        (
            "outputs/robustness/e001_geographic_fold_manifest.json",
            "2575232a392925eedcbabe343e599df58a789137bad3b356b3774e9ef9637157",
        ),
    ),
)
def test_phase_2d_and_2e_a_artifacts_are_immutable(relative_path: str, expected: str) -> None:
    observed = hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()
    assert observed == expected

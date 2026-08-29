"""Fail-closed, coordinate-free terrain feature loading for E001 modelling."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from archaeoai.dataset import BACKGROUND_LABEL, POSITIVE_LABEL
from archaeoai.terrain.full_dataset import load_processed_archive, terrain_content_digest

REPRESENTATION_CONFIGS: dict[str, tuple[str, ...]] = {
    "normalized_elevation": ("elevation_normalized",),
    "slope": ("slope_degrees",),
    "hillshade": ("hillshade_315_45",),
    "local_relief": ("local_relief_r16m",),
    "all_four": (
        "elevation_normalized",
        "slope_degrees",
        "hillshade_315_45",
        "local_relief_r16m",
    ),
}
ALLOWED_PARTITIONS = frozenset({"train", "development"})


class FinalTestAccessError(PermissionError):
    """Raised whenever Phase 2D-A code requests a final-test partition."""


@dataclass(frozen=True, slots=True)
class SafeIndexRow:
    sample_id: str
    partition: str
    class_label: str | None
    patch_sha256: str | None
    qa_status: str | None
    provenance_id: str | None
    survey_year: str | None
    geographic_block_id: str | None
    source_resolution_m: str | None


@dataclass(frozen=True, slots=True)
class LoadedPartition:
    features: np.ndarray
    labels: np.ndarray
    sample_ids: tuple[str, ...]


def mean_pool_4x4(values: np.ndarray) -> np.ndarray:
    """Pool one 128×128 representation into 1,024 deterministic features."""
    array = np.asarray(values, dtype=np.float32)
    if array.shape != (128, 128):
        raise ValueError("mean pooling requires a 128x128 representation")
    blocks = array.reshape(32, 4, 32, 4)
    finite = np.isfinite(blocks)
    counts = finite.sum(axis=(1, 3))
    totals = np.where(finite, blocks, 0).sum(axis=(1, 3), dtype=np.float64)
    pooled = np.zeros((32, 32), dtype=np.float32)
    np.divide(totals, counts, out=pooled, where=counts > 0)
    return pooled.reshape(1024)


def configuration_hash(payload: dict[str, object]) -> str:
    content = {key: value for key, value in payload.items() if key != "config_sha256"}
    encoded = json.dumps(content, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def validate_frozen_primary_config(path: str | Path) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("frozen") is not True:
        raise ValueError("primary configuration is not frozen")
    expected = payload.get("config_sha256")
    if not isinstance(expected, str) or configuration_hash(payload) != expected:
        raise ValueError("frozen primary configuration hash mismatch")
    return payload


def authorize_final_test(
    primary_config_path: str | Path,
    split_manifest_path: str | Path,
    *,
    condition: str,
) -> dict[str, object]:
    """Validate the frozen config/split binding required by any future final evaluator."""
    payload = validate_frozen_primary_config(primary_config_path)
    manifest = json.loads(Path(split_manifest_path).read_text(encoding="utf-8"))
    split_hashes = payload.get("split_hashes")
    if not isinstance(split_hashes, dict):
        raise ValueError("frozen configuration omits split hashes")
    if split_hashes.get(condition) != manifest.get("assignment_sha256"):
        raise ValueError("frozen configuration does not authorize this final-test split")
    if payload.get("selection_condition") != condition:
        raise ValueError("frozen configuration was selected for another condition")
    return payload


class DevelopmentDataLoader:
    """Load only an active condition's train/development data; final test is inaccessible."""

    def __init__(self, project_root: Path, *, condition: str = "geographic") -> None:
        if condition not in {"random", "geographic"}:
            raise ValueError("unsupported split condition")
        self.project_root = project_root.resolve()
        self.condition = condition
        self.manifest = json.loads(
            (self.project_root / f"outputs/dataset/e001_{condition}_split_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        if self.manifest.get("frozen") is not True:
            raise ValueError("active split manifest is not frozen")
        self.rows = self._read_and_verify_index()

    def _read_and_verify_index(self) -> tuple[SafeIndexRow, ...]:
        path = self.project_root / "outputs/dataset/e001_modelling_index.csv"
        digest = hashlib.sha256()
        rows = []
        with path.open(encoding="utf-8-sig", newline="") as file:
            source_rows = sorted(csv.DictReader(file), key=lambda row: row["sample_id"])
        for source in source_rows:
            partition = source[f"split_{self.condition}"]
            digest.update(f"{source['sample_id']}:{partition}\n".encode())
            final_test = partition == "final_test"
            rows.append(
                SafeIndexRow(
                    sample_id=source["sample_id"],
                    partition=partition,
                    class_label=None if final_test else source["class_label"],
                    patch_sha256=None if final_test else source["patch_sha256"],
                    qa_status=None if final_test else source["qa_status"],
                    provenance_id=None if final_test else source["provenance_id"],
                    survey_year=None if final_test else source["survey_year"],
                    geographic_block_id=None if final_test else source["geographic_block_id"],
                    source_resolution_m=None if final_test else source["source_resolution_m"],
                )
            )
        if digest.hexdigest() != self.manifest.get("assignment_sha256"):
            raise ValueError("active split assignment hash mismatch")
        return tuple(rows)

    def _private_archive(self, row: SafeIndexRow) -> Path:
        if row.class_label == POSITIVE_LABEL:
            subdirectory = "terrain/processed"
        elif row.class_label == BACKGROUND_LABEL:
            subdirectory = "backgrounds/processed"
        else:
            raise ValueError("model label must come from the safe index")
        return self.project_root / "data/private/e001" / subdirectory / f"{row.sample_id}.npz"

    def load_partition(self, partition: str, representation: str) -> LoadedPartition:
        if partition not in ALLOWED_PARTITIONS:
            raise FinalTestAccessError("Phase 2D-A permits only train and development")
        channels = REPRESENTATION_CONFIGS.get(representation)
        if channels is None:
            raise ValueError("unknown representation configuration")
        selected = [row for row in self.rows if row.partition == partition]
        if not selected:
            raise ValueError(f"active split has no {partition} rows")
        features = []
        labels = []
        sample_ids = []
        for row in selected:
            if row.qa_status != "pass" or row.patch_sha256 is None:
                raise ValueError("only QA-passed non-final rows may be loaded")
            elevation, mask, representations = load_processed_archive(self._private_archive(row))
            if terrain_content_digest(elevation, mask) != row.patch_sha256:
                raise ValueError(f"terrain content checksum mismatch for {row.sample_id}")
            features.append(
                np.concatenate([mean_pool_4x4(representations[name]) for name in channels])
            )
            labels.append(1 if row.class_label == POSITIVE_LABEL else 0)
            sample_ids.append(row.sample_id)
        matrix = np.asarray(features, dtype=np.float32)
        if not np.isfinite(matrix).all():
            raise ValueError("pooled model features must be finite")
        return LoadedPartition(
            features=matrix,
            labels=np.asarray(labels, dtype=np.int8),
            sample_ids=tuple(sample_ids),
        )

    def allowed_metadata_rows(self, partition: str) -> tuple[SafeIndexRow, ...]:
        if partition not in ALLOWED_PARTITIONS:
            raise FinalTestAccessError("final-test metadata are inaccessible during Phase 2D-A")
        return tuple(row for row in self.rows if row.partition == partition)

"""Coordinate-safe E001 modelling-index records and validation."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

from archaeoai.terrain.privacy import assert_coordinate_safe_mapping

POSITIVE_LABEL = "positive_bowl_barrow"
BACKGROUND_LABEL = "unlabelled_background"
CLASS_LABELS = frozenset({POSITIVE_LABEL, BACKGROUND_LABEL})
PARTITIONS = frozenset({"train", "development", "final_test"})


@dataclass(frozen=True, slots=True)
class DatasetRecord:
    sample_id: str
    class_label: str
    observation_group_id: str
    overlap_component_id: str
    geographic_block_id: str
    survey_year: str
    provenance_id: str
    source_resolution_m: float
    patch_size_m: int
    processing_version: str
    qa_status: str
    sampling_stratum: str
    patch_sha256: str
    split_random: str
    split_geographic: str


DATASET_FIELDS = tuple(DatasetRecord.__dataclass_fields__)


def validate_dataset_index(records: list[DatasetRecord]) -> None:
    if not records:
        raise ValueError("dataset index cannot be empty")
    if len({record.sample_id for record in records}) != len(records):
        raise ValueError("duplicate sample ID")
    if len({record.patch_sha256 for record in records}) != len(records):
        raise ValueError("duplicate terrain content")
    for record in records:
        assert_coordinate_safe_mapping(asdict(record))
        if record.class_label not in CLASS_LABELS:
            raise ValueError("unsupported class label")
        if record.qa_status != "pass":
            raise ValueError("dataset index may contain only QA-passed records")
        if record.split_random not in PARTITIONS or record.split_geographic not in PARTITIONS:
            raise ValueError("unsupported split partition")
        if len(record.patch_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in record.patch_sha256
        ):
            raise ValueError("patch checksum must be lowercase SHA-256")
    counts = {label: sum(row.class_label == label for row in records) for label in CLASS_LABELS}
    if len(set(counts.values())) != 1:
        raise ValueError("the primary E001 dataset must remain class-balanced")


def write_dataset_index(records: list[DatasetRecord], destination: Path) -> None:
    validate_dataset_index(records)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=DATASET_FIELDS)
        writer.writeheader()
        writer.writerows(asdict(record) for record in records)

"""Coordinate-safe E001 terrain index and geographic integrity checks."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

from archaeoai.terrain.acquisition import PrivateSiteLocation
from archaeoai.terrain.patches import patch_bounds
from archaeoai.terrain.privacy import assert_coordinate_safe_mapping


@dataclass(frozen=True, slots=True)
class TerrainIndexRecord:
    sample_id: str
    nhle_list_entry: int
    geographic_group_id: str
    terrain_provenance_id: str
    survey_year: str
    source_resolution_m: float
    processing_version: str
    patch_size_m: int
    representations: str
    qa_status: str
    patch_sha256: str


INDEX_FIELDS = tuple(TerrainIndexRecord.__dataclass_fields__)


def validate_index(records: list[TerrainIndexRecord]) -> None:
    for record in records:
        assert_coordinate_safe_mapping(asdict(record))
        if record.qa_status not in {"pass", "rejected"}:
            raise ValueError(f"unsupported terrain QA status: {record.qa_status}")
        if len(record.patch_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in record.patch_sha256
        ):
            raise ValueError("patch_sha256 must be a lowercase SHA-256 digest")
    if len({record.sample_id for record in records}) != len(records):
        raise ValueError("duplicate terrain sample ID")
    if len({record.nhle_list_entry for record in records}) != len(records):
        raise ValueError("duplicate NHLE source observation")
    groups_by_source: dict[int, set[str]] = {}
    for record in records:
        groups_by_source.setdefault(record.nhle_list_entry, set()).add(record.geographic_group_id)
    if any(len(groups) != 1 for groups in groups_by_source.values()):
        raise ValueError("one source observation appears in multiple geographic groups")


def write_index(records: list[TerrainIndexRecord], destination: Path) -> None:
    validate_index(records)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=INDEX_FIELDS)
        writer.writeheader()
        writer.writerows(asdict(record) for record in records)


def cross_group_patch_overlaps(
    locations: tuple[PrivateSiteLocation, ...], *, patch_size_m: float
) -> tuple[tuple[int, int], ...]:
    """Return only safe source-ID pairs whose future patches overlap across groups."""
    conflicts = []
    for index, first in enumerate(locations):
        first_bounds = patch_bounds((first.easting, first.northing), patch_size_m=patch_size_m)
        for second in locations[index + 1 :]:
            if first.geographic_group_id == second.geographic_group_id:
                continue
            second_bounds = patch_bounds(
                (second.easting, second.northing), patch_size_m=patch_size_m
            )
            overlaps = (
                first_bounds.left < second_bounds.right
                and first_bounds.right > second_bounds.left
                and first_bounds.bottom < second_bounds.top
                and first_bounds.top > second_bounds.bottom
            )
            if overlaps:
                conflicts.append(tuple(sorted((first.list_entry, second.list_entry))))
    return tuple(sorted(conflicts))

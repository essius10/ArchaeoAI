"""Deterministic leakage-resistant split primitives for E001."""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from dataclasses import replace

from archaeoai.dataset import BACKGROUND_LABEL, POSITIVE_LABEL, DatasetRecord

RANDOM_SPLIT_SEED = "E001-group-aware-random-v1-2026-08-29"
SPLIT_VERSION = "e001-splits-v1"
GEOGRAPHIC_DEVELOPMENT_GROUPS = frozenset({"BNG_100KM_E2_N0"})
GEOGRAPHIC_FINAL_TEST_GROUPS = frozenset({"BNG_100KM_E3_N2", "BNG_100KM_E5_N4"})


def _rank(group_id: str, *, seed: str) -> str:
    return hashlib.sha256(f"{seed}:{group_id}".encode()).hexdigest()


def _groups(records: list[DatasetRecord]) -> dict[str, list[DatasetRecord]]:
    grouped: dict[str, list[DatasetRecord]] = defaultdict(list)
    for record in records:
        grouped[record.observation_group_id].append(record)
    return dict(grouped)


def _positive_weight(records: list[DatasetRecord]) -> int:
    return sum(record.class_label == POSITIVE_LABEL for record in records)


def _take_groups(
    remaining: list[tuple[str, list[DatasetRecord]]], *, target_positive_count: int
) -> tuple[set[str], list[tuple[str, list[DatasetRecord]]]]:
    selected: set[str] = set()
    outstanding = target_positive_count
    deferred: list[tuple[str, list[DatasetRecord]]] = []
    for group_id, rows in remaining:
        weight = _positive_weight(rows)
        if weight <= outstanding:
            selected.add(group_id)
            outstanding -= weight
        else:
            deferred.append((group_id, rows))
        if outstanding == 0:
            deferred.extend(item for item in remaining if item[0] not in selected)
            unique = {group_id: rows for group_id, rows in deferred if group_id not in selected}
            return selected, list(unique.items())
    raise ValueError("group weights cannot satisfy requested split count")


def assign_group_aware_random(
    records: list[DatasetRecord],
    *,
    development_positive_count: int,
    final_test_positive_count: int,
    seed: str = RANDOM_SPLIT_SEED,
) -> list[DatasetRecord]:
    grouped = _groups(records)
    ranked = sorted(grouped.items(), key=lambda item: _rank(item[0], seed=seed))
    final_groups, remaining = _take_groups(ranked, target_positive_count=final_test_positive_count)
    development_groups, _ = _take_groups(
        remaining, target_positive_count=development_positive_count
    )
    assigned = []
    for record in records:
        partition = (
            "final_test"
            if record.observation_group_id in final_groups
            else "development"
            if record.observation_group_id in development_groups
            else "train"
        )
        assigned.append(replace(record, split_random=partition))
    validate_split_integrity(assigned, condition="random")
    return assigned


def assign_geographic(
    records: list[DatasetRecord],
    *,
    development_groups: frozenset[str] = GEOGRAPHIC_DEVELOPMENT_GROUPS,
    final_test_groups: frozenset[str] = GEOGRAPHIC_FINAL_TEST_GROUPS,
) -> list[DatasetRecord]:
    if development_groups & final_test_groups:
        raise ValueError("geographic development and final-test groups overlap")
    observed = {record.geographic_block_id for record in records}
    if not development_groups <= observed or not final_test_groups <= observed:
        raise ValueError("frozen geographic split references an absent block")
    assigned = []
    for record in records:
        partition = (
            "final_test"
            if record.geographic_block_id in final_test_groups
            else "development"
            if record.geographic_block_id in development_groups
            else "train"
        )
        assigned.append(replace(record, split_geographic=partition))
    validate_split_integrity(assigned, condition="geographic")
    return assigned


def validate_split_integrity(records: list[DatasetRecord], *, condition: str) -> None:
    if condition not in {"random", "geographic"}:
        raise ValueError("unknown split condition")
    attribute = f"split_{condition}"
    sample_ids = [record.sample_id for record in records]
    if len(sample_ids) != len(set(sample_ids)):
        raise ValueError("sample ID appears more than once")
    grouped = _groups(records)
    if any(len({getattr(row, attribute) for row in rows}) != 1 for rows in grouped.values()):
        raise ValueError("observation group crosses split partitions")
    components: dict[str, set[str]] = defaultdict(set)
    for record in records:
        if record.overlap_component_id:
            components[record.overlap_component_id].add(getattr(record, attribute))
    if any(len(partitions) != 1 for partitions in components.values()):
        raise ValueError("overlap component crosses split partitions")
    if condition == "geographic":
        blocks: dict[str, set[str]] = defaultdict(set)
        for record in records:
            blocks[record.geographic_block_id].add(record.split_geographic)
        if any(len(partitions) != 1 for partitions in blocks.values()):
            raise ValueError("geographic block crosses split partitions")
    for partition in ("train", "development", "final_test"):
        class_counts = Counter(
            record.class_label for record in records if getattr(record, attribute) == partition
        )
        if class_counts[POSITIVE_LABEL] != class_counts[BACKGROUND_LABEL]:
            raise ValueError(f"{condition} {partition} is not class-balanced")


def assignment_digest(records: list[DatasetRecord], *, condition: str) -> str:
    attribute = f"split_{condition}"
    digest = hashlib.sha256()
    for record in sorted(records, key=lambda row: row.sample_id):
        digest.update(f"{record.sample_id}:{getattr(record, attribute)}\n".encode())
    return digest.hexdigest()


def validate_frozen_assignment(
    records: list[DatasetRecord], *, condition: str, expected_digest: str
) -> None:
    validate_split_integrity(records, condition=condition)
    if assignment_digest(records, condition=condition) != expected_digest:
        raise ValueError(f"frozen {condition} split assignment changed")


def terrain_windows_overlap(
    first: tuple[float, float], second: tuple[float, float], *, patch_size_m: float
) -> bool:
    """Return whether equal, axis-aligned square terrain windows overlap in area."""
    return abs(first[0] - second[0]) < patch_size_m and abs(first[1] - second[1]) < patch_size_m


def cross_partition_window_overlaps(
    samples: list[tuple[str, str, tuple[float, float]]], *, patch_size_m: float
) -> list[tuple[str, str]]:
    collisions = []
    for index, (first_id, first_partition, first_centre) in enumerate(samples):
        for second_id, second_partition, second_centre in samples[index + 1 :]:
            if first_partition != second_partition and terrain_windows_overlap(
                first_centre, second_centre, patch_size_m=patch_size_m
            ):
                collisions.append((first_id, second_id))
    return collisions


def cross_partition_distance_violations(
    samples: list[tuple[str, str, tuple[float, float]]], *, minimum_m: float
) -> list[tuple[str, str]]:
    violations = []
    for index, (first_id, first_partition, first_centre) in enumerate(samples):
        for second_id, second_partition, second_centre in samples[index + 1 :]:
            if first_partition != second_partition:
                distance = (
                    (first_centre[0] - second_centre[0]) ** 2
                    + (first_centre[1] - second_centre[1]) ** 2
                ) ** 0.5
                if distance < minimum_m:
                    violations.append((first_id, second_id))
    return violations

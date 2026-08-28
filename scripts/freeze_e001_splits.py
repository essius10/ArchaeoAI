"""Build the coordinate-safe E001 dataset index and freeze both split conditions."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from archaeoai.dataset import (
    BACKGROUND_LABEL,
    POSITIVE_LABEL,
    DatasetRecord,
    validate_dataset_index,
    write_dataset_index,
)
from archaeoai.paths import find_project_root
from archaeoai.splits import (
    GEOGRAPHIC_DEVELOPMENT_GROUPS,
    GEOGRAPHIC_FINAL_TEST_GROUPS,
    RANDOM_SPLIT_SEED,
    SPLIT_VERSION,
    assign_geographic,
    assign_group_aware_random,
    assignment_digest,
    validate_frozen_assignment,
)
from archaeoai.terrain.background import observation_group_id
from archaeoai.terrain.privacy import assert_coordinate_safe_mapping

DEVELOPMENT_POSITIVE_COUNT = 14
FINAL_TEST_POSITIVE_COUNT = 31


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _base_records(root: Path) -> list[DatasetRecord]:
    positives = _read_csv(root / "outputs/terrain/e001_terrain_index.csv")
    backgrounds = _read_csv(root / "outputs/background/e001_background_index.csv")
    if len(positives) != 261 or len(backgrounds) != 261:
        raise ValueError("the frozen 1:1 source indexes must each contain 261 rows")
    positive_records = []
    component_by_group: dict[str, str] = {}
    for row in positives:
        identity = row["overlap_group_id"] or row["sample_id"]
        group_id = observation_group_id(identity)
        component_by_group[group_id] = row["overlap_group_id"]
        positive_records.append(
            DatasetRecord(
                sample_id=row["sample_id"],
                class_label=POSITIVE_LABEL,
                observation_group_id=group_id,
                overlap_component_id=row["overlap_group_id"],
                geographic_block_id=row["geographic_group_id"],
                survey_year=row["survey_year"],
                provenance_id=row["terrain_provenance_id"],
                source_resolution_m=float(row["source_resolution_m"]),
                patch_size_m=int(row["patch_size_m"]),
                processing_version=row["processing_version"],
                qa_status=row["qa_status"],
                sampling_stratum="positive_curated",
                patch_sha256=row["patch_sha256"],
                split_random="train",
                split_geographic="train",
            )
        )
    background_records = [
        DatasetRecord(
            sample_id=row["sample_id"],
            class_label=BACKGROUND_LABEL,
            observation_group_id=row["observation_group_id"],
            overlap_component_id=component_by_group.get(row["observation_group_id"], ""),
            geographic_block_id=row["geographic_group_id"],
            survey_year=row["survey_year"],
            provenance_id=row["terrain_provenance_id"],
            source_resolution_m=float(row["source_resolution_m"]),
            patch_size_m=int(row["patch_size_m"]),
            processing_version=row["processing_version"],
            qa_status=row["qa_status"],
            sampling_stratum=row["sampling_stratum"],
            patch_sha256=row["patch_sha256"],
            split_random="train",
            split_geographic="train",
        )
        for row in backgrounds
    ]
    records = positive_records + background_records
    validate_dataset_index(records)
    grouped: dict[str, Counter[str]] = defaultdict(Counter)
    for record in records:
        grouped[record.observation_group_id][record.class_label] += 1
    if any(counts[POSITIVE_LABEL] != counts[BACKGROUND_LABEL] for counts in grouped.values()):
        raise ValueError("every observational group must be class-balanced")
    return records


def _partition_summary(records: list[DatasetRecord], attribute: str) -> dict[str, object]:
    summary: dict[str, object] = {}
    for partition in ("train", "development", "final_test"):
        rows = [record for record in records if getattr(record, attribute) == partition]
        summary[partition] = {
            "observations": len(rows),
            "positives": sum(record.class_label == POSITIVE_LABEL for record in rows),
            "backgrounds": sum(record.class_label == BACKGROUND_LABEL for record in rows),
            "observation_groups": len({record.observation_group_id for record in rows}),
            "geographic_groups": sorted({record.geographic_block_id for record in rows}),
            "survey_years": dict(sorted(Counter(record.survey_year for record in rows).items())),
            "provenance_ids": dict(
                sorted(Counter(record.provenance_id for record in rows).items())
            ),
            "source_resolutions_m": dict(
                sorted(Counter(str(record.source_resolution_m) for record in rows).items())
            ),
        }
    return summary


def _write_manifest(path: Path, payload: dict[str, object]) -> None:
    assert_coordinate_safe_mapping(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    root = find_project_root()
    records = _base_records(root)
    records = assign_group_aware_random(
        records,
        development_positive_count=DEVELOPMENT_POSITIVE_COUNT,
        final_test_positive_count=FINAL_TEST_POSITIVE_COUNT,
    )
    records = assign_geographic(records)
    random_digest = assignment_digest(records, condition="random")
    geographic_digest = assignment_digest(records, condition="geographic")
    validate_frozen_assignment(records, condition="random", expected_digest=random_digest)
    validate_frozen_assignment(records, condition="geographic", expected_digest=geographic_digest)
    output_root = root / "outputs/dataset"
    write_dataset_index(records, output_root / "e001_modelling_index.csv")
    common: dict[str, object] = {
        "schema_version": "e001-split-manifest-v1",
        "split_version": SPLIT_VERSION,
        "creation_date": "2026-08-29",
        "frozen": True,
        "class_labels": [POSITIVE_LABEL, BACKGROUND_LABEL],
        "total_observations": len(records),
        "grouping_rules": [
            "matched positive and background records remain together",
            "all retained positive overlap-component members and their backgrounds remain together",
            "each terrain representation remains part of its one source observation",
        ],
        "overlap_policy": "retain_grouped; components may never cross partitions",
        "final_test_change_guard": "assignment SHA-256 must match this manifest",
    }
    random_manifest = {
        **common,
        "condition": "group_aware_random",
        "algorithm": "SHA-256-ranked observational groups with exact pre-specified class targets",
        "seed": RANDOM_SPLIT_SEED,
        "target_positive_counts": {
            "development": DEVELOPMENT_POSITIVE_COUNT,
            "final_test": FINAL_TEST_POSITIVE_COUNT,
        },
        "assignment_sha256": random_digest,
        "partitions": _partition_summary(records, "split_random"),
        "rationale": (
            "A non-spatial comparison with the same development and final-test class counts as "
            "the geographic condition, while keeping related observations inseparable."
        ),
    }
    geographic_manifest = {
        **common,
        "condition": "geographic_holdout",
        "algorithm": "complete frozen BNG 100 km block assignment",
        "seed": None,
        "development_groups": sorted(GEOGRAPHIC_DEVELOPMENT_GROUPS),
        "final_test_groups": sorted(GEOGRAPHIC_FINAL_TEST_GROUPS),
        "assignment_sha256": geographic_digest,
        "partitions": _partition_summary(records, "split_geographic"),
        "final_test_block_envelope_separation_km": 141.421,
        "minimum_cross_partition_centre_buffer_m": 1000,
        "candidate_designs_considered_without_modelling": [
            {
                "groups": ["BNG_100KM_E3_N2", "BNG_100KM_E5_N4"],
                "positive_count": 31,
                "decision": "selected_final_test",
            },
            {
                "groups": ["BNG_100KM_E3_N5"],
                "positive_count": 15,
                "decision": "not_selected_single_block_and_smaller_test",
            },
            {
                "groups": ["BNG_100KM_E2_N0"],
                "positive_count": 14,
                "decision": "selected_development",
            },
            {
                "groups": ["BNG_100KM_E4_N5"],
                "positive_count": 15,
                "decision": "not_selected_provenance_concentration",
            },
        ],
        "rationale": (
            "Two nonadjacent final blocks provide 31 positives and matched backgrounds. A separate "
            "southwestern block supports development without exposing the final geographic test."
        ),
    }
    _write_manifest(output_root / "e001_random_split_manifest.json", random_manifest)
    _write_manifest(output_root / "e001_geographic_split_manifest.json", geographic_manifest)
    print(json.dumps({"random": random_manifest, "geographic": geographic_manifest}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

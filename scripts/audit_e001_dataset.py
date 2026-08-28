"""Run coordinate-private leakage, duplicate, provenance, and confound audits for E001."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median

import numpy as np

from archaeoai.dataset import DatasetRecord, validate_dataset_index
from archaeoai.paths import find_project_root
from archaeoai.splits import (
    cross_partition_distance_violations,
    cross_partition_window_overlaps,
    validate_frozen_assignment,
    validate_split_integrity,
)
from archaeoai.terrain.acquisition import PrivateSiteLocation, opaque_sample_id
from archaeoai.terrain.background import euclidean_distance, geographic_group_id
from archaeoai.terrain.full_dataset import load_processed_archive
from archaeoai.terrain.privacy import (
    assert_coordinate_safe_mapping,
    verify_git_ignored,
)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _load_dataset(path: Path) -> list[DatasetRecord]:
    records = []
    for row in _read_csv(path):
        records.append(
            DatasetRecord(
                sample_id=row["sample_id"],
                class_label=row["class_label"],
                observation_group_id=row["observation_group_id"],
                overlap_component_id=row["overlap_component_id"],
                geographic_block_id=row["geographic_block_id"],
                survey_year=row["survey_year"],
                provenance_id=row["provenance_id"],
                source_resolution_m=float(row["source_resolution_m"]),
                patch_size_m=int(row["patch_size_m"]),
                processing_version=row["processing_version"],
                qa_status=row["qa_status"],
                sampling_stratum=row["sampling_stratum"],
                patch_sha256=row["patch_sha256"],
                split_random=row["split_random"],
                split_geographic=row["split_geographic"],
            )
        )
    return records


def _load_private_centres(root: Path) -> dict[str, tuple[float, float]]:
    positive_path = root / "data/private/e001/approved-site-locations.json"
    background_path = root / "data/private/e001/backgrounds/sampling_state.json"
    verify_git_ignored(root, positive_path)
    verify_git_ignored(root, background_path)
    positive_payload = json.loads(positive_path.read_text(encoding="utf-8"))
    background_payload = json.loads(background_path.read_text(encoding="utf-8"))
    centres = {}
    for item in positive_payload["records"]:
        location = PrivateSiteLocation(**item)
        centres[opaque_sample_id(location.list_entry)] = (location.easting, location.northing)
    for item in background_payload["records"].values():
        if isinstance(item, dict) and "easting" in item:
            centres[str(item["sample_id"])] = (float(item["easting"]), float(item["northing"]))
    if len(centres) != 522:
        raise ValueError("private audit requires all 522 sample centres")
    return centres


def _count_distance_violations(
    first: list[tuple[float, float]],
    second: list[tuple[float, float]],
    *,
    minimum_m: float,
    same_collection: bool = False,
) -> int:
    count = 0
    for first_index, first_centre in enumerate(first):
        start = first_index + 1 if same_collection else 0
        count += sum(
            euclidean_distance(first_centre, second_centre) < minimum_m
            for second_centre in second[start:]
        )
    return count


def _descriptive_confound_summary(records: list[DatasetRecord], root: Path) -> dict[str, object]:
    values: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for record in records:
        private_class = (
            "terrain/processed"
            if record.class_label == "positive_bowl_barrow"
            else ("backgrounds/processed")
        )
        archive_path = root / "data/private/e001" / private_class / f"{record.sample_id}.npz"
        elevation, _mask, representations = load_processed_archive(archive_path)
        values[record.class_label]["patch_median_elevation_m"].append(
            float(np.nanmedian(elevation))
        )
        values[record.class_label]["patch_mean_slope_degrees"].append(
            float(np.nanmean(representations["slope_degrees"]))
        )
        values[record.class_label]["patch_mean_abs_local_relief_m"].append(
            float(np.nanmean(np.abs(representations["local_relief_r16m"])))
        )
    summary: dict[str, object] = {}
    for label, metrics in values.items():
        summary[label] = {
            metric: {
                "median": round(median(measurements), 6),
                "q25": round(float(np.percentile(measurements, 25)), 6),
                "q75": round(float(np.percentile(measurements, 75)), 6),
            }
            for metric, measurements in metrics.items()
        }
    return summary


def main() -> int:
    root = find_project_root()
    dataset_path = root / "outputs/dataset/e001_modelling_index.csv"
    records = _load_dataset(dataset_path)
    validate_dataset_index(records)
    random_manifest = json.loads(
        (root / "outputs/dataset/e001_random_split_manifest.json").read_text(encoding="utf-8")
    )
    geographic_manifest = json.loads(
        (root / "outputs/dataset/e001_geographic_split_manifest.json").read_text(encoding="utf-8")
    )
    validate_frozen_assignment(
        records,
        condition="random",
        expected_digest=random_manifest["assignment_sha256"],
    )
    validate_frozen_assignment(
        records,
        condition="geographic",
        expected_digest=geographic_manifest["assignment_sha256"],
    )
    validate_split_integrity(records, condition="random")
    validate_split_integrity(records, condition="geographic")
    centres = _load_private_centres(root)
    positives = [
        centres[row.sample_id] for row in records if row.class_label == "positive_bowl_barrow"
    ]
    backgrounds = [
        centres[row.sample_id] for row in records if row.class_label == "unlabelled_background"
    ]
    positive_background_violations = _count_distance_violations(
        positives, backgrounds, minimum_m=500
    )
    background_spacing_violations = _count_distance_violations(
        backgrounds, backgrounds, minimum_m=256, same_collection=True
    )
    geographic_mismatches = sum(
        geographic_group_id(centres[row.sample_id]) != row.geographic_block_id for row in records
    )
    cross_partition: dict[str, int] = {}
    geographic_buffer_violations = 0
    for condition in ("random", "geographic"):
        samples = [
            (row.sample_id, getattr(row, f"split_{condition}"), centres[row.sample_id])
            for row in records
        ]
        cross_partition[condition] = len(cross_partition_window_overlaps(samples, patch_size_m=128))
        if condition == "geographic":
            geographic_buffer_violations = len(
                cross_partition_distance_violations(samples, minimum_m=1000)
            )
    class_joint_distributions = {}
    for label in ("positive_bowl_barrow", "unlabelled_background"):
        class_joint_distributions[label] = dict(
            sorted(
                Counter(
                    (row.geographic_block_id, row.provenance_id, row.survey_year)
                    for row in records
                    if row.class_label == label
                ).items()
            )
        )
    joint_balance = (
        class_joint_distributions["positive_bowl_barrow"]
        == class_joint_distributions["unlabelled_background"]
    )
    visual = json.loads(
        (root / "outputs/background/e001_background_pilot40_visual_qa.json").read_text(
            encoding="utf-8"
        )
    )
    summary: dict[str, object] = {
        "phase": "2C dataset freeze audit",
        "counts": {
            "positives": 261,
            "unlabelled_backgrounds": 261,
            "total_observations": len(records),
            "observation_groups": len({row.observation_group_id for row in records}),
            "overlap_components": len(
                {row.overlap_component_id for row in records if row.overlap_component_id}
            ),
        },
        "hard_leakage_audit": {
            "duplicate_sample_ids": len(records) - len({row.sample_id for row in records}),
            "duplicate_patch_digests": len(records) - len({row.patch_sha256 for row in records}),
            "positive_background_buffer_violations": positive_background_violations,
            "background_spacing_violations": background_spacing_violations,
            "geographic_assignment_mismatches": geographic_mismatches,
            "random_cross_partition_window_overlaps": cross_partition["random"],
            "geographic_cross_partition_window_overlaps": cross_partition["geographic"],
            "geographic_cross_partition_1km_buffer_violations": geographic_buffer_violations,
            "random_group_integrity": "pass",
            "geographic_group_integrity": "pass",
            "overlap_component_integrity": "pass",
            "frozen_assignment_digests": "pass",
        },
        "provenance_and_geography_audit": {
            "class_joint_distribution_exactly_matched": joint_balance,
            "provenance_class_correlation_by_design": "none_observed_in_counts",
            "geographic_class_correlation_by_design": "none_observed_in_counts",
        },
        "descriptive_confound_audit": _descriptive_confound_summary(records, root),
        "modern_feature_visual_audit": {
            "sample_size": visual["sample_size"],
            "passed": visual["passed"],
            "hard_invalid": visual["hard_invalid"],
            "observation_counts": visual["observation_counts"],
            "interpretation": (
                "Realistic hard confounds were retained; visual appearance was not used as an "
                "archaeological label filter."
            ),
        },
        "privacy": {
            "coordinate_bearing_inputs_private_and_ignored": True,
            "coordinates_or_sampling_geometry_tracked": False,
            "audit_output_aggregate_only": True,
        },
        "scope": {
            "model_trained": False,
            "metrics_computed": False,
            "predictions_inspected": False,
        },
    }
    assert_coordinate_safe_mapping(summary)
    hard_values = summary["hard_leakage_audit"]
    assert isinstance(hard_values, dict)
    numeric_failures = [value for value in hard_values.values() if isinstance(value, int) and value]
    if numeric_failures or not joint_balance:
        raise ValueError("E001 dataset freeze audit failed")
    destination = root / "outputs/dataset/e001_dataset_audit.json"
    destination.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

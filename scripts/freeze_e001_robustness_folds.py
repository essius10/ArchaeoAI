"""Freeze score-independent E001 post-hoc geographic robustness folds."""

from __future__ import annotations

import csv
import json
from collections import Counter

from archaeoai.paths import find_project_root
from archaeoai.robustness import (
    FOLD_COUNT,
    ROBUSTNESS_LABEL,
    deterministic_geographic_folds,
    fold_assignment_hash,
    read_robustness_index,
    validate_fold_assignments,
)
from archaeoai.splits import cross_partition_window_overlaps
from archaeoai.terrain.acquisition import PrivateSiteLocation, opaque_sample_id
from archaeoai.terrain.privacy import assert_coordinate_safe_mapping, verify_git_ignored


def _private_centres(root):
    positive_path = root / "data/private/e001/approved-site-locations.json"
    background_path = root / "data/private/e001/backgrounds/sampling_state.json"
    verify_git_ignored(root, positive_path)
    verify_git_ignored(root, background_path)
    positive = json.loads(positive_path.read_text(encoding="utf-8"))
    background = json.loads(background_path.read_text(encoding="utf-8"))
    centres = {
        opaque_sample_id(location.list_entry): (location.easting, location.northing)
        for item in positive["records"]
        for location in (PrivateSiteLocation(**item),)
    }
    centres.update(
        {
            str(item["sample_id"]): (float(item["easting"]), float(item["northing"]))
            for item in background["records"].values()
            if isinstance(item, dict) and "easting" in item
        }
    )
    if len(centres) != 522:
        raise ValueError("fold leakage audit requires 522 private centres")
    return centres


def main() -> int:
    root = find_project_root()
    output_root = root / "outputs/robustness"
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / "e001_geographic_fold_manifest.json"
    groups_path = output_root / "e001_geographic_fold_groups.csv"
    if manifest_path.exists() or groups_path.exists():
        raise FileExistsError("refusing to overwrite frozen robustness folds")
    records = read_robustness_index(root / "outputs/dataset/e001_modelling_index.csv")
    assignments = deterministic_geographic_folds(records)
    fold_counts = validate_fold_assignments(records, assignments)
    centres = _private_centres(root)
    samples = [
        (
            record.sample_id,
            f"fold_{assignments[record.geographic_block_id] + 1}",
            centres[record.sample_id],
        )
        for record in records
    ]
    overlap_violations = cross_partition_window_overlaps(samples, patch_size_m=128)
    if overlap_violations:
        raise ValueError("terrain windows overlap across geographic robustness folds")
    group_class_counts = Counter(
        (record.geographic_block_id, record.class_label) for record in records
    )
    group_rows = [
        {
            "geographic_block_id": group,
            "fold": f"fold_{fold + 1}",
            "positive_bowl_barrow": group_class_counts[(group, "positive_bowl_barrow")],
            "unlabelled_background": group_class_counts[(group, "unlabelled_background")],
        }
        for group, fold in sorted(assignments.items(), key=lambda item: (item[1], item[0]))
    ]
    manifest = {
        "schema_version": "e001-posthoc-geographic-folds-v1",
        "analysis_label": ROBUSTNESS_LABEL,
        "created_before_robustness_scoring": True,
        "algorithm": (
            "sort whole BNG groups by descending observation count, descending related-unit "
            "count, then group ID; greedily assign to the fold with the fewest observations, "
            "fewest groups, then lowest fold number"
        ),
        "fold_count": FOLD_COUNT,
        "assignment_sha256": fold_assignment_hash(assignments),
        "folds": {f"fold_{fold + 1}": counts for fold, counts in fold_counts.items()},
        "geographic_group_assignments": {
            group: f"fold_{fold + 1}" for group, fold in sorted(assignments.items())
        },
        "integrity": {
            "geographic_groups_kept_whole": True,
            "matched_and_overlap_units_kept_whole": True,
            "cross_fold_terrain_window_overlaps": 0,
            "coordinates_written": False,
            "model_scores_used": False,
        },
    }
    assert_coordinate_safe_mapping(manifest)
    with groups_path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=group_rows[0])
        writer.writeheader()
        writer.writerows(group_rows)
    with manifest_path.open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Deterministic, post-hoc robustness utilities for E001."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier

from archaeoai.dataset import BACKGROUND_LABEL, POSITIVE_LABEL

ROBUSTNESS_LABEL = "posthoc_geographic_robustness"
FOLD_COUNT = 5
MODEL_SEEDS = (20260829, 20260830, 20260831, 20260901, 20260902)
TRAINING_FRACTIONS = (1.0, 0.75, 0.5, 0.25)
BOOTSTRAP_SEEDS = (20260835, 20260836, 20260837)
PERMUTATION_SEEDS = tuple(range(20261000, 20261100))
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
    "all_minus_elevation": (
        "slope_degrees",
        "hillshade_315_45",
        "local_relief_r16m",
    ),
    "all_minus_slope": (
        "elevation_normalized",
        "hillshade_315_45",
        "local_relief_r16m",
    ),
    "all_minus_hillshade": (
        "elevation_normalized",
        "slope_degrees",
        "local_relief_r16m",
    ),
    "all_minus_local_relief": (
        "elevation_normalized",
        "slope_degrees",
        "hillshade_315_45",
    ),
}


@dataclass(frozen=True, slots=True)
class RobustnessRecord:
    sample_id: str
    class_label: str
    observation_group_id: str
    overlap_component_id: str
    geographic_block_id: str
    provenance_id: str
    survey_year: str
    source_resolution_m: str
    patch_sha256: str
    qa_status: str

    @property
    def related_unit_id(self) -> str:
        return self.overlap_component_id or self.observation_group_id


def read_robustness_index(path: Path) -> tuple[RobustnessRecord, ...]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        source = list(csv.DictReader(handle))
    records = tuple(
        RobustnessRecord(
            sample_id=row["sample_id"],
            class_label=row["class_label"],
            observation_group_id=row["observation_group_id"],
            overlap_component_id=row["overlap_component_id"],
            geographic_block_id=row["geographic_block_id"],
            provenance_id=row["provenance_id"],
            survey_year=row["survey_year"],
            source_resolution_m=row["source_resolution_m"],
            patch_sha256=row["patch_sha256"],
            qa_status=row["qa_status"],
        )
        for row in source
    )
    if len(records) != 522 or len({record.sample_id for record in records}) != 522:
        raise ValueError("robustness index must contain 522 unique observations")
    if Counter(record.class_label for record in records) != Counter(
        {POSITIVE_LABEL: 261, BACKGROUND_LABEL: 261}
    ):
        raise ValueError("robustness index class counts changed")
    if not all(record.qa_status == "pass" for record in records):
        raise ValueError("robustness analysis requires QA-passed observations")
    return records


def deterministic_geographic_folds(
    records: tuple[RobustnessRecord, ...], *, fold_count: int = FOLD_COUNT
) -> dict[str, int]:
    """Greedily balance whole BNG groups by size without using model scores."""
    if fold_count < 2:
        raise ValueError("geographic robustness requires at least two folds")
    class_counts: dict[str, Counter[str]] = defaultdict(Counter)
    units_by_group: dict[str, set[str]] = defaultdict(set)
    for record in records:
        class_counts[record.geographic_block_id][record.class_label] += 1
        units_by_group[record.geographic_block_id].add(record.related_unit_id)
    if len(class_counts) < fold_count:
        raise ValueError("fewer geographic groups than folds")
    for counts in class_counts.values():
        if counts[POSITIVE_LABEL] != counts[BACKGROUND_LABEL]:
            raise ValueError("each geographic group must retain matched class counts")
    ordered_groups = sorted(
        class_counts,
        key=lambda group: (
            -sum(class_counts[group].values()),
            -len(units_by_group[group]),
            group,
        ),
    )
    fold_totals = [0] * fold_count
    fold_group_counts = [0] * fold_count
    assignments = {}
    for group in ordered_groups:
        fold = min(
            range(fold_count),
            key=lambda index: (fold_totals[index], fold_group_counts[index], index),
        )
        assignments[group] = fold
        fold_totals[fold] += sum(class_counts[group].values())
        fold_group_counts[fold] += 1
    return assignments


def validate_fold_assignments(
    records: tuple[RobustnessRecord, ...], assignments: dict[str, int]
) -> dict[int, dict[str, int]]:
    observed_groups = {record.geographic_block_id for record in records}
    if set(assignments) != observed_groups:
        raise ValueError("fold assignments do not cover every geographic group exactly once")
    related_folds: dict[str, set[int]] = defaultdict(set)
    counts: dict[int, Counter[str]] = defaultdict(Counter)
    groups: dict[int, set[str]] = defaultdict(set)
    for record in records:
        fold = assignments[record.geographic_block_id]
        related_folds[record.related_unit_id].add(fold)
        counts[fold][record.class_label] += 1
        groups[fold].add(record.geographic_block_id)
    if any(len(folds) != 1 for folds in related_folds.values()):
        raise ValueError("related or overlapping observations cross robustness folds")
    if set(counts) != set(range(FOLD_COUNT)):
        raise ValueError("robustness fold numbering changed")
    output = {}
    for fold in range(FOLD_COUNT):
        if counts[fold][POSITIVE_LABEL] != counts[fold][BACKGROUND_LABEL]:
            raise ValueError("robustness fold class balance changed")
        output[fold] = {
            "observations": sum(counts[fold].values()),
            "positive_bowl_barrow": counts[fold][POSITIVE_LABEL],
            "unlabelled_background": counts[fold][BACKGROUND_LABEL],
            "geographic_groups": len(groups[fold]),
            "related_units": len(
                {
                    record.related_unit_id
                    for record in records
                    if assignments[record.geographic_block_id] == fold
                }
            ),
        }
    return output


def fold_assignment_hash(assignments: dict[str, int]) -> str:
    digest = hashlib.sha256()
    for group, fold in sorted(assignments.items()):
        digest.update(f"{group}:fold_{fold + 1}\n".encode())
    return digest.hexdigest()


def deterministic_training_units(
    records: tuple[RobustnessRecord, ...],
    *,
    test_fold: int,
    assignments: dict[str, int],
    fraction: float,
) -> set[str]:
    if fraction not in TRAINING_FRACTIONS:
        raise ValueError("training fraction was not pre-specified")
    units = sorted(
        {
            record.related_unit_id
            for record in records
            if assignments[record.geographic_block_id] != test_fold
        }
    )
    if fraction == 1.0:
        return set(units)
    target = max(1, round(len(units) * fraction))
    ranked = sorted(
        units,
        key=lambda unit: hashlib.sha256(
            f"e001-phase-2e-training-v1:{test_fold}:{fraction:.2f}:{unit}".encode()
        ).hexdigest(),
    )
    return set(ranked[:target])


def build_frozen_random_forest(seed: int) -> RandomForestClassifier:
    if seed not in MODEL_SEEDS and seed not in PERMUTATION_SEEDS:
        raise ValueError("Random Forest seed was not pre-specified")
    return RandomForestClassifier(
        n_estimators=300,
        max_depth=8,
        min_samples_leaf=5,
        max_features="sqrt",
        n_jobs=1,
        random_state=seed,
    )


def robustness_protocol_hash(payload: dict[str, object]) -> str:
    content = {key: value for key, value in payload.items() if key != "protocol_sha256"}
    encoded = json.dumps(content, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def validate_robustness_protocol(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected = payload.get("protocol_sha256")
    if not isinstance(expected, str) or robustness_protocol_hash(payload) != expected:
        raise ValueError("robustness protocol hash mismatch")
    if payload.get("frozen_before_robustness_scoring") is not True:
        raise ValueError("robustness protocol was not frozen before scoring")
    if payload.get("analysis_label") != ROBUSTNESS_LABEL:
        raise ValueError("robustness analysis label changed")
    if payload.get("model_seeds") != list(MODEL_SEEDS):
        raise ValueError("robustness model seeds changed")
    if payload.get("training_fractions") != list(TRAINING_FRACTIONS):
        raise ValueError("training fractions changed")
    if payload.get("bootstrap_seeds") != list(BOOTSTRAP_SEEDS):
        raise ValueError("bootstrap seeds changed")
    if payload.get("permutation_seeds") != list(PERMUTATION_SEEDS):
        raise ValueError("permutation seeds changed")
    return payload

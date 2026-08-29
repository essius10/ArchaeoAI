"""Run the frozen, post-hoc E001 Phase 2E-A robustness analyses."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import statistics
import subprocess
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
import scipy
import sklearn

from archaeoai.dataset import BACKGROUND_LABEL, POSITIVE_LABEL
from archaeoai.final_evaluation import (
    group_bootstrap_intervals,
    load_final_partition,
    load_final_training_partition,
    metric_values,
)
from archaeoai.model_data import mean_pool_4x4
from archaeoai.paths import find_project_root
from archaeoai.robustness import (
    BOOTSTRAP_SEEDS,
    FOLD_COUNT,
    MODEL_SEEDS,
    PERMUTATION_SEEDS,
    REPRESENTATION_CONFIGS,
    ROBUSTNESS_LABEL,
    TRAINING_FRACTIONS,
    RobustnessRecord,
    build_frozen_random_forest,
    deterministic_geographic_folds,
    deterministic_training_units,
    fold_assignment_hash,
    read_robustness_index,
    validate_fold_assignments,
    validate_robustness_protocol,
)
from archaeoai.terrain.full_dataset import load_processed_archive, terrain_content_digest
from archaeoai.terrain.privacy import assert_coordinate_safe_mapping

OUTPUT_NAMES = (
    "e001_geographic_cv.csv",
    "e001_group_performance.csv",
    "e001_representation_ablation.csv",
    "e001_drop_one_representation.csv",
    "e001_seed_sensitivity.csv",
    "e001_training_fraction.csv",
    "e001_permutation_diagnostic.json",
    "e001_robustness_summary.json",
)


def _git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_pre_run(root: Path, protocol: dict[str, object]) -> None:
    output_root = root / "outputs/robustness"
    if any((output_root / name).exists() for name in OUTPUT_NAMES):
        raise FileExistsError("refusing to overwrite an existing robustness result")
    if _git(root, "status", "--porcelain"):
        raise ValueError("robustness scoring requires a clean committed protocol state")
    if protocol["confirmatory_result_remains_phase_2d"] is not True:
        raise ValueError("protocol does not preserve the confirmatory Phase 2D result")
    for relative, expected in protocol["original_result_file_sha256"].items():
        if _file_sha256(root / relative) != expected:
            raise ValueError("an original Phase 2D result file changed")


def _private_archive(root: Path, record: RobustnessRecord) -> Path:
    subdirectory = (
        "terrain/processed" if record.class_label == POSITIVE_LABEL else "backgrounds/processed"
    )
    return root / "data/private/e001" / subdirectory / f"{record.sample_id}.npz"


def _load_features(
    root: Path, records: tuple[RobustnessRecord, ...]
) -> tuple[dict[str, np.ndarray], np.ndarray, tuple[dict[str, float], ...]]:
    pooled = {channel: [] for channel in REPRESENTATION_CONFIGS["all_four"]}
    labels = []
    terrain_summaries = []
    for record in records:
        elevation, mask, representations = load_processed_archive(_private_archive(root, record))
        if terrain_content_digest(elevation, mask) != record.patch_sha256:
            raise ValueError("robustness terrain checksum mismatch")
        for channel in pooled:
            pooled[channel].append(mean_pool_4x4(representations[channel]))
        labels.append(1 if record.class_label == POSITIVE_LABEL else 0)
        terrain_summaries.append(
            {
                "median_absolute_elevation_m": float(np.nanmedian(elevation)),
                "mean_slope_degrees": float(np.nanmean(representations["slope_degrees"])),
                "mean_absolute_local_relief_m": float(
                    np.nanmean(np.abs(representations["local_relief_r16m"]))
                ),
                "missing_fraction": float(np.mean(mask)),
            }
        )
    matrices = {key: np.asarray(values, dtype=np.float32) for key, values in pooled.items()}
    if any(matrix.shape != (522, 1024) for matrix in matrices.values()):
        raise ValueError("robustness feature matrices changed shape")
    if not all(np.isfinite(matrix).all() for matrix in matrices.values()):
        raise ValueError("robustness feature matrices contain non-finite values")
    return matrices, np.asarray(labels, dtype=np.int8), tuple(terrain_summaries)


def _representation_matrix(matrices: dict[str, np.ndarray], name: str) -> np.ndarray:
    channels = REPRESENTATION_CONFIGS[name]
    return np.concatenate([matrices[channel] for channel in channels], axis=1)


def _indices_for_fold(
    records: tuple[RobustnessRecord, ...], assignments: dict[str, int], fold: int
) -> tuple[np.ndarray, np.ndarray]:
    test = np.asarray(
        [
            index
            for index, record in enumerate(records)
            if assignments[record.geographic_block_id] == fold
        ]
    )
    train = np.asarray(
        [
            index
            for index, record in enumerate(records)
            if assignments[record.geographic_block_id] != fold
        ]
    )
    return train, test


def _evaluate(
    features: np.ndarray,
    labels: np.ndarray,
    train_indices: np.ndarray,
    test_indices: np.ndarray,
    *,
    seed: int,
) -> tuple[dict[str, object], np.ndarray, np.ndarray]:
    estimator = build_frozen_random_forest(seed)
    estimator.fit(features[train_indices], labels[train_indices])
    probabilities = estimator.predict_proba(features[test_indices])[:, 1]
    predictions = (probabilities >= 0.5).astype(np.int8)
    return (
        metric_values(labels[test_indices], predictions, probabilities),
        predictions,
        probabilities,
    )


def _flat_metrics_row(prefix: dict[str, object], metrics: dict[str, object]) -> dict[str, object]:
    matrix = metrics["confusion_matrix"]
    return {
        **prefix,
        **{
            key: metrics[key]
            for key in (
                "balanced_accuracy",
                "accuracy",
                "precision",
                "recall",
                "f1",
                "roc_auc",
                "average_precision",
            )
        },
        "tn_background_correct": matrix[
            "true_unlabelled_background_predicted_unlabelled_background"
        ],
        "fp_background_predicted_positive": matrix[
            "true_unlabelled_background_predicted_positive_bowl_barrow"
        ],
        "fn_positive_predicted_background": matrix[
            "true_positive_bowl_barrow_predicted_unlabelled_background"
        ],
        "tp_positive_correct": matrix["true_positive_bowl_barrow_predicted_positive_bowl_barrow"],
    }


def _write_csv_exclusive(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _balanced_accuracy_summary(rows: list[dict[str, object]]) -> dict[str, float]:
    values = [float(row["balanced_accuracy"]) for row in rows]
    return {
        "mean": float(statistics.mean(values)),
        "median": float(statistics.median(values)),
        "population_standard_deviation": float(statistics.pstdev(values)),
        "minimum": min(values),
        "maximum": max(values),
    }


def _aggregate_score_distribution(values: np.ndarray) -> dict[str, float]:
    return {
        "count": int(len(values)),
        "minimum": float(np.min(values)),
        "q25": float(np.percentile(values, 25)),
        "median": float(np.median(values)),
        "mean": float(np.mean(values)),
        "q75": float(np.percentile(values, 75)),
        "maximum": float(np.max(values)),
    }


def _error_audit(
    records: tuple[RobustnessRecord, ...],
    labels: np.ndarray,
    predictions: np.ndarray,
    terrain_summaries: tuple[dict[str, float], ...],
) -> dict[str, object]:
    metadata = {}
    for field in ("geographic_block_id", "provenance_id", "survey_year", "source_resolution_m"):
        categories: dict[str, Counter[str]] = defaultdict(Counter)
        for record, label, prediction in zip(records, labels, predictions, strict=True):
            counts = categories[str(getattr(record, field))]
            counts["positive_bowl_barrow" if label == 1 else "unlabelled_background"] += 1
            counts["correct" if label == prediction else "error"] += 1
        metadata[field] = {
            category: dict(sorted(counts.items()))
            for category, counts in sorted(categories.items())
        }
    terrain = {}
    for status in ("correct", "error"):
        selected = [
            summary
            for summary, label, prediction in zip(
                terrain_summaries, labels, predictions, strict=True
            )
            if (label == prediction) == (status == "correct")
        ]
        terrain[status] = {
            "observations": len(selected),
            **{
                name: {
                    "mean": float(np.mean([item[name] for item in selected])),
                    "median": float(np.median([item[name] for item in selected])),
                }
                for name in terrain_summaries[0]
            },
        }
    return {
        "metadata_counts_and_errors": metadata,
        "terrain_summary_by_correctness": terrain,
        "hard_confounds": (
            "Forestry, road/track, field-boundary, and hard-relief flags are unavailable "
            "consistently and were not inferred from predictions."
        ),
    }


def _classification(
    primary: dict[str, float],
    seed_rows: list[dict[str, object]],
    training_rows: list[dict[str, object]],
) -> tuple[str, str, dict[str, object]]:
    seed_means = []
    for seed in MODEL_SEEDS:
        seed_values = [float(row["balanced_accuracy"]) for row in seed_rows if row["seed"] == seed]
        seed_means.append(statistics.mean(seed_values))
    half_mean = statistics.mean(
        float(row["balanced_accuracy"]) for row in training_rows if row["training_fraction"] == 0.5
    )
    criteria = {
        "no_direct_shortcut_failure": True,
        "primary_mean_at_least_0_70": primary["mean"] >= 0.70,
        "minimum_fold_at_least_0_60": primary["minimum"] >= 0.60,
        "seed_mean_range_at_most_0_05": max(seed_means) - min(seed_means) <= 0.05,
        "half_training_mean_at_least_0_65": half_mean >= 0.65,
        "seed_mean_range": max(seed_means) - min(seed_means),
        "half_training_mean": half_mean,
    }
    if all(
        value is True
        for key, value in criteria.items()
        if key not in {"seed_mean_range", "half_training_mean"}
    ):
        classification = "ROBUST"
    elif primary["mean"] >= 0.60 and primary["minimum"] >= 0.50:
        classification = "MIXED ROBUSTNESS"
    else:
        classification = "FRAGILE"
    recommendation = (
        "GO FOR PHASE 2E-B STRONGER MODELS"
        if classification == "ROBUST"
        else "STAY WITH BASELINE / COLLECT MORE DATA"
    )
    return classification, recommendation, criteria


def main() -> int:
    root = find_project_root()
    output_root = root / "outputs/robustness"
    protocol = validate_robustness_protocol(
        root / "configs/e001-phase-2e-a-robustness-protocol.json"
    )
    _validate_pre_run(root, protocol)
    records = read_robustness_index(root / "outputs/dataset/e001_modelling_index.csv")
    assignments = deterministic_geographic_folds(records)
    fold_counts = validate_fold_assignments(records, assignments)
    if fold_assignment_hash(assignments) != protocol["geographic_folds"]["assignment_sha256"]:
        raise ValueError("robustness fold hash differs from the frozen protocol")
    matrices, labels, terrain_summaries = _load_features(root, records)
    all_four = _representation_matrix(matrices, "all_four")

    primary_rows = []
    primary_cache = {}
    oof_predictions = np.full(len(records), -1, dtype=np.int8)
    oof_probabilities = np.full(len(records), np.nan, dtype=np.float64)
    for fold in range(FOLD_COUNT):
        train, test = _indices_for_fold(records, assignments, fold)
        metrics, predictions, probabilities = _evaluate(
            all_four, labels, train, test, seed=MODEL_SEEDS[0]
        )
        oof_predictions[test] = predictions
        oof_probabilities[test] = probabilities
        primary_cache[fold] = (metrics, predictions, probabilities)
        primary_rows.append(
            _flat_metrics_row(
                {
                    "analysis_label": ROBUSTNESS_LABEL,
                    "fold": f"fold_{fold + 1}",
                    "train_n": len(train),
                    "test_n": len(test),
                    "positive_bowl_barrow_n": fold_counts[fold]["positive_bowl_barrow"],
                    "unlabelled_background_n": fold_counts[fold]["unlabelled_background"],
                    "geographic_group_n": fold_counts[fold]["geographic_groups"],
                },
                metrics,
            )
        )
    if np.any(oof_predictions < 0) or not np.isfinite(oof_probabilities).all():
        raise ValueError("primary robustness predictions are incomplete")
    primary_summary = _balanced_accuracy_summary(primary_rows)

    representation_rows = []
    for representation in (
        "normalized_elevation",
        "slope",
        "hillshade",
        "local_relief",
        "all_four",
        "all_minus_elevation",
        "all_minus_slope",
        "all_minus_hillshade",
        "all_minus_local_relief",
    ):
        features = _representation_matrix(matrices, representation)
        for fold in range(FOLD_COUNT):
            train, test = _indices_for_fold(records, assignments, fold)
            metrics = (
                primary_cache[fold][0]
                if representation == "all_four"
                else _evaluate(features, labels, train, test, seed=MODEL_SEEDS[0])[0]
            )
            representation_rows.append(
                _flat_metrics_row(
                    {
                        "analysis_label": ROBUSTNESS_LABEL,
                        "representation": representation,
                        "feature_count": features.shape[1],
                        "fold": f"fold_{fold + 1}",
                    },
                    metrics,
                )
            )

    seed_rows = []
    for seed in MODEL_SEEDS:
        for fold in range(FOLD_COUNT):
            train, test = _indices_for_fold(records, assignments, fold)
            metrics = (
                primary_cache[fold][0]
                if seed == MODEL_SEEDS[0]
                else _evaluate(all_four, labels, train, test, seed=seed)[0]
            )
            seed_rows.append(
                _flat_metrics_row(
                    {
                        "analysis_label": ROBUSTNESS_LABEL,
                        "seed": seed,
                        "fold": f"fold_{fold + 1}",
                    },
                    metrics,
                )
            )

    training_rows = []
    for fraction in TRAINING_FRACTIONS:
        for fold in range(FOLD_COUNT):
            full_train, test = _indices_for_fold(records, assignments, fold)
            selected_units = deterministic_training_units(
                records, test_fold=fold, assignments=assignments, fraction=fraction
            )
            train = np.asarray(
                [
                    index
                    for index in full_train
                    if records[int(index)].related_unit_id in selected_units
                ]
            )
            if (
                np.bincount(labels[train], minlength=2).tolist()[0]
                != np.bincount(labels[train], minlength=2).tolist()[1]
            ):
                raise ValueError("training subsample lost class balance")
            metrics = (
                primary_cache[fold][0]
                if fraction == 1.0
                else _evaluate(all_four, labels, train, test, seed=MODEL_SEEDS[0])[0]
            )
            training_rows.append(
                _flat_metrics_row(
                    {
                        "analysis_label": ROBUSTNESS_LABEL,
                        "training_fraction": fraction,
                        "fold": f"fold_{fold + 1}",
                        "train_n": len(train),
                        "train_positive_n": int(np.sum(labels[train] == 1)),
                        "train_background_n": int(np.sum(labels[train] == 0)),
                        "training_related_units": len(selected_units),
                    },
                    metrics,
                )
            )

    group_rows = []
    for group in sorted(assignments):
        indices = np.asarray(
            [index for index, record in enumerate(records) if record.geographic_block_id == group]
        )
        metrics = metric_values(
            labels[indices], oof_predictions[indices], oof_probabilities[indices]
        )
        group_rows.append(
            _flat_metrics_row(
                {
                    "analysis_label": ROBUSTNESS_LABEL,
                    "geographic_block_id": group,
                    "fold": f"fold_{assignments[group] + 1}",
                    "n": len(indices),
                    "positive_bowl_barrow_n": int(np.sum(labels[indices] == 1)),
                    "unlabelled_background_n": int(np.sum(labels[indices] == 0)),
                },
                metrics,
            )
        )

    with (root / "outputs/dataset/e001_modelling_index.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        index_rows = list(csv.DictReader(handle))
    geographic_train = np.asarray(
        [index for index, row in enumerate(index_rows) if row["split_geographic"] == "train"]
    )
    geographic_development = np.asarray(
        [index for index, row in enumerate(index_rows) if row["split_geographic"] == "development"]
    )
    permutation_rows = []
    for seed in PERMUTATION_SEEDS:
        shuffled = np.random.default_rng(seed).permutation(labels[geographic_train])
        estimator = build_frozen_random_forest(MODEL_SEEDS[0])
        estimator.fit(all_four[geographic_train], shuffled)
        probabilities = estimator.predict_proba(all_four[geographic_development])[:, 1]
        predictions = (probabilities >= 0.5).astype(np.int8)
        metrics = metric_values(labels[geographic_development], predictions, probabilities)
        permutation_rows.append(
            {
                "seed": seed,
                "balanced_accuracy": metrics["balanced_accuracy"],
                "roc_auc": metrics["roc_auc"],
            }
        )
    selected_development_score = 0.8214285714285714
    permutation_values = [row["balanced_accuracy"] for row in permutation_rows]
    permutation_output = {
        "analysis_label": ROBUSTNESS_LABEL,
        "scope": "frozen geographic Phase 2D-A train/development",
        "runs": len(permutation_rows),
        "model_seed": MODEL_SEEDS[0],
        "results": permutation_rows,
        "mean_balanced_accuracy": float(statistics.mean(permutation_values)),
        "median_balanced_accuracy": float(statistics.median(permutation_values)),
        "minimum_balanced_accuracy": min(permutation_values),
        "maximum_balanced_accuracy": max(permutation_values),
        "selected_development_balanced_accuracy": selected_development_score,
        "exploratory_plus_one_tail_fraction": (
            1 + sum(value >= selected_development_score for value in permutation_values)
        )
        / (len(permutation_values) + 1),
        "used_for_selection_or_tuning": False,
    }

    final_training = load_final_training_partition(root, "geographic")
    final_partition = load_final_partition(
        root,
        condition="geographic",
        expected_split_hash=protocol["phase_2d_split_hashes"]["geographic"],
    )
    final_estimator = build_frozen_random_forest(MODEL_SEEDS[0])
    final_estimator.fit(final_training.features, final_training.labels)
    final_probabilities = final_estimator.predict_proba(final_partition.features)[:, 1]
    final_predictions = (final_probabilities >= 0.5).astype(np.int8)
    bootstrap_seed_sensitivity = {
        str(seed): group_bootstrap_intervals(
            final_partition,
            final_predictions,
            final_probabilities,
            iterations=int(protocol["bootstrap_iterations_per_seed"]),
            seed=seed,
        )["intervals"]["balanced_accuracy"]
        for seed in BOOTSTRAP_SEEDS
    }

    channel_order = list(REPRESENTATION_CONFIGS["all_four"])
    correlation = np.corrcoef(
        np.stack([matrices[channel].reshape(-1) for channel in channel_order])
    )
    representation_correlation = {
        first: {second: float(correlation[i, j]) for j, second in enumerate(channel_order)}
        for i, first in enumerate(channel_order)
    }
    score_distributions = {
        POSITIVE_LABEL: _aggregate_score_distribution(oof_probabilities[labels == 1]),
        BACKGROUND_LABEL: _aggregate_score_distribution(oof_probabilities[labels == 0]),
        "warning": (
            "Random Forest scores are uncalibrated classifier scores, not archaeological "
            "probabilities."
        ),
    }
    error_audit = _error_audit(records, labels, oof_predictions, terrain_summaries)
    classification, recommendation, classification_evidence = _classification(
        primary_summary, seed_rows, training_rows
    )
    representation_summaries = {
        name: _balanced_accuracy_summary(
            [row for row in representation_rows if row["representation"] == name]
        )
        for name in REPRESENTATION_CONFIGS
    }
    seed_summaries = {
        str(seed): _balanced_accuracy_summary([row for row in seed_rows if row["seed"] == seed])
        for seed in MODEL_SEEDS
    }
    training_summaries = {
        str(fraction): _balanced_accuracy_summary(
            [row for row in training_rows if row["training_fraction"] == fraction]
        )
        for fraction in TRAINING_FRACTIONS
    }
    summary = {
        "schema_version": "e001-phase-2e-a-robustness-results-v1",
        "analysis_label": ROBUSTNESS_LABEL,
        "posthoc_not_confirmatory": True,
        "evaluation_timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "protocol_sha256": protocol["protocol_sha256"],
        "protocol_commit": _git(root, "rev-parse", "HEAD"),
        "original_phase_2d_result": protocol["original_phase_2d_result"],
        "original_result_files_unchanged": True,
        "fold_assignment_sha256": fold_assignment_hash(assignments),
        "primary_geographic_cv": {
            "folds": primary_rows,
            "summary": primary_summary,
        },
        "representation_summaries": representation_summaries,
        "seed_summaries": seed_summaries,
        "training_fraction_summaries": training_summaries,
        "group_extremes": {
            "easiest": sorted(
                group_rows, key=lambda row: (-row["balanced_accuracy"], row["geographic_block_id"])
            )[:5],
            "hardest": sorted(
                group_rows, key=lambda row: (row["balanced_accuracy"], row["geographic_block_id"])
            )[:5],
        },
        "score_distributions": score_distributions,
        "representation_feature_correlation": representation_correlation,
        "bootstrap_seed_sensitivity": bootstrap_seed_sensitivity,
        "permutation_diagnostic_summary": {
            key: value for key, value in permutation_output.items() if key != "results"
        },
        "error_and_confound_audit": error_audit,
        "shortcut_audit": {
            "absolute_elevation_in_features": False,
            "per_patch_median_normalization_offset_invariance_tested": True,
            "sample_id_path_filename_or_serialization_metadata_in_features": False,
            "npz_key_order_compression_path_and_name_invariance_tested": True,
            "cross_fold_terrain_window_overlaps": 0,
            "matched_and_overlap_units_cross_folds": 0,
            "metadata_used_as_features": False,
            "all_missing_fractions_zero": all(
                summary_item["missing_fraction"] == 0.0 for summary_item in terrain_summaries
            ),
        },
        "hard_background_stress": protocol["hard_background_stress"],
        "model_complexity_diagnostic": protocol["model_complexity_diagnostic"],
        "robustness_classification": classification,
        "classification_evidence": classification_evidence,
        "recommendation": recommendation,
        "no_phase_2d_reselection_or_retuning": True,
        "software_versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "privacy": {
            "aggregate_only": True,
            "coordinates_written": False,
            "sample_identifiers_written": False,
            "maps_created": False,
        },
    }
    assert_coordinate_safe_mapping(summary)
    single_names = {
        "normalized_elevation",
        "slope",
        "hillshade",
        "local_relief",
        "all_four",
    }
    _write_csv_exclusive(output_root / "e001_geographic_cv.csv", primary_rows)
    _write_csv_exclusive(output_root / "e001_group_performance.csv", group_rows)
    _write_csv_exclusive(
        output_root / "e001_representation_ablation.csv",
        [row for row in representation_rows if row["representation"] in single_names],
    )
    _write_csv_exclusive(
        output_root / "e001_drop_one_representation.csv",
        [row for row in representation_rows if row["representation"] not in single_names],
    )
    _write_csv_exclusive(output_root / "e001_seed_sensitivity.csv", seed_rows)
    _write_csv_exclusive(output_root / "e001_training_fraction.csv", training_rows)
    with (output_root / "e001_permutation_diagnostic.json").open("x", encoding="utf-8") as handle:
        json.dump(permutation_output, handle, indent=2)
        handle.write("\n")
    with (output_root / "e001_robustness_summary.json").open("x", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
        handle.write("\n")
    for relative, expected in protocol["original_result_file_sha256"].items():
        if _file_sha256(root / relative) != expected:
            raise ValueError("original Phase 2D result changed during robustness analysis")
    print(
        json.dumps(
            {
                "primary_geographic_cv": primary_summary,
                "robustness_classification": classification,
                "recommendation": recommendation,
                "permutation_mean": permutation_output["mean_balanced_accuracy"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

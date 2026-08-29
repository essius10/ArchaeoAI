"""Run the hash-bound E001 random and geographic final evaluations exactly once."""

from __future__ import annotations

import csv
import json
import platform
import subprocess
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import scipy
import sklearn

from archaeoai.final_evaluation import (
    EXPECTED_SELECTION_COMMIT,
    curve_values,
    fit_and_evaluate,
    group_bootstrap_intervals,
    load_final_partition,
    load_final_training_partition,
    validate_final_protocol,
)
from archaeoai.paths import find_project_root
from archaeoai.terrain.privacy import assert_coordinate_safe_mapping

RESULT_PATHS = (
    "outputs/modelling/e001_final_results.csv",
    "outputs/modelling/e001_random_vs_geographic.json",
    "outputs/modelling/e001_final_model_audit.json",
)


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments], cwd=root, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def _assert_pre_unlock_state(root: Path, protocol: dict[str, object]) -> None:
    for relative in RESULT_PATHS:
        if (root / relative).exists():
            raise FileExistsError(f"refusing to overwrite final result: {relative}")
    if _git(root, "status", "--porcelain"):
        raise ValueError("final evaluation requires a clean committed protocol state")
    if _git(root, "merge-base", "--is-ancestor", EXPECTED_SELECTION_COMMIT, "HEAD"):
        raise ValueError("unexpected merge-base output")
    protocol_commit = _git(root, "rev-parse", "HEAD")
    if protocol_commit == EXPECTED_SELECTION_COMMIT:
        raise ValueError("final protocol must be committed after the selection commit")
    if protocol.get("no_retuning_after_unlock") is not True:
        raise ValueError("protocol does not forbid retuning")


def _aggregate_error_and_shortcut_audit(
    final: object, predictions: np.ndarray, terrain_summaries: tuple[dict[str, float], ...]
) -> dict[str, object]:
    rows = final.rows
    labels = final.labels
    metadata_fields = ("geographic_block_id", "provenance_id", "survey_year", "source_resolution_m")
    metadata = {}
    for field in metadata_fields:
        values = defaultdict(lambda: Counter())
        for row, label, prediction in zip(rows, labels, predictions, strict=True):
            category = str(getattr(row, field))
            values[category]["positive_bowl_barrow" if label == 1 else "unlabelled_background"] += 1
            values[category]["correct" if label == prediction else "error"] += 1
        metadata[field] = {
            category: dict(sorted(counts.items())) for category, counts in sorted(values.items())
        }
    terrain = {}
    for correctness in ("correct", "error"):
        selected = [
            summary
            for summary, label, prediction in zip(
                terrain_summaries, labels, predictions, strict=True
            )
            if (label == prediction) == (correctness == "correct")
        ]
        terrain[correctness] = {
            "observations": len(selected),
            **{
                name: {
                    "mean": float(np.mean([item[name] for item in selected])) if selected else None,
                    "median": float(np.median([item[name] for item in selected]))
                    if selected
                    else None,
                }
                for name in (
                    "median_absolute_elevation_m",
                    "mean_slope_degrees",
                    "mean_absolute_local_relief_m",
                    "missing_fraction",
                )
            },
        }
    return {
        "metadata_counts_and_errors": metadata,
        "terrain_summary_by_correctness": terrain,
        "feature_policy": {
            "model_features": [
                "elevation_normalized",
                "slope_degrees",
                "hillshade_315_45",
                "local_relief_r16m",
            ],
            "metadata_features": [],
            "identifier_path_or_filename_features": [],
            "raw_absolute_elevation_is_model_feature": False,
            "class_specific_serialization_schema": False,
        },
        "flag_limit": (
            "Hard-relief, forestry, and road/track flags are unavailable consistently for all "
            "final observations and were not inferred post hoc."
        ),
    }


def _write_csv_exclusive(path: Path, result: dict[str, object]) -> None:
    fieldnames = [
        "condition",
        "role",
        "n",
        "positive_bowl_barrow_n",
        "unlabelled_background_n",
        "balanced_accuracy",
        "balanced_accuracy_ci95_lower",
        "balanced_accuracy_ci95_upper",
        "accuracy",
        "precision",
        "recall",
        "f1",
        "roc_auc",
        "average_precision",
        "tn_background_correct",
        "fp_background_predicted_positive",
        "fn_positive_predicted_background",
        "tp_positive_correct",
    ]
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for condition in ("random", "geographic"):
            item = result["conditions"][condition]
            metrics = item["metrics"]
            interval = item["bootstrap"]["intervals"]["balanced_accuracy"]
            matrix = metrics["confusion_matrix"]
            writer.writerow(
                {
                    "condition": condition,
                    "role": item["role"],
                    "n": item["counts"]["total"],
                    "positive_bowl_barrow_n": item["counts"]["positive_bowl_barrow"],
                    "unlabelled_background_n": item["counts"]["unlabelled_background"],
                    "balanced_accuracy": metrics["balanced_accuracy"],
                    "balanced_accuracy_ci95_lower": interval["lower"],
                    "balanced_accuracy_ci95_upper": interval["upper"],
                    "accuracy": metrics["accuracy"],
                    "precision": metrics["precision"],
                    "recall": metrics["recall"],
                    "f1": metrics["f1"],
                    "roc_auc": metrics["roc_auc"],
                    "average_precision": metrics["average_precision"],
                    "tn_background_correct": matrix[
                        "true_unlabelled_background_predicted_unlabelled_background"
                    ],
                    "fp_background_predicted_positive": matrix[
                        "true_unlabelled_background_predicted_positive_bowl_barrow"
                    ],
                    "fn_positive_predicted_background": matrix[
                        "true_positive_bowl_barrow_predicted_unlabelled_background"
                    ],
                    "tp_positive_correct": matrix[
                        "true_positive_bowl_barrow_predicted_positive_bowl_barrow"
                    ],
                }
            )


def main() -> int:
    root = find_project_root()
    protocol_path = root / "configs/e001-phase-2d-b-final-protocol.json"
    config_path = root / "outputs/modelling/e001_primary_baseline_config.json"
    protocol, config = validate_final_protocol(protocol_path, config_path)
    _assert_pre_unlock_state(root, protocol)
    unlock_timestamp = datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(timespec="seconds")
    condition_outputs = {}
    diagnostic_payloads = {}
    for condition in ("random", "geographic"):
        training = load_final_training_partition(root, condition)
        final = load_final_partition(
            root,
            condition=condition,
            expected_split_hash=config["split_hashes"][condition],
        )
        metrics, predictions, probabilities = fit_and_evaluate(
            training, final, threshold=float(config["classification_threshold"])
        )
        bootstrap = group_bootstrap_intervals(
            final,
            predictions,
            probabilities,
            iterations=int(protocol["bootstrap"]["iterations"]),
            seed=int(protocol["bootstrap"]["seed"]),
        )
        condition_outputs[condition] = {
            "role": "primary_scientific_endpoint"
            if condition == "geographic"
            else "secondary_descriptive_comparison",
            "training_count": len(training.labels),
            "counts": {
                "total": len(final.labels),
                "positive_bowl_barrow": int(np.sum(final.labels == 1)),
                "unlabelled_background": int(np.sum(final.labels == 0)),
            },
            "metrics": metrics,
            "bootstrap": bootstrap,
            "curves": curve_values(final.labels, probabilities),
        }
        diagnostic_payloads[condition] = _aggregate_error_and_shortcut_audit(
            final, predictions, final.terrain_summaries
        )
    random_score = condition_outputs["random"]["metrics"]["balanced_accuracy"]
    geographic_score = condition_outputs["geographic"]["metrics"]["balanced_accuracy"]
    result = {
        "schema_version": "e001-final-results-v1",
        "phase": "2D-B one-way final baseline evaluation",
        "final_test_evaluated": True,
        "evaluation_timestamp": unlock_timestamp,
        "selection_commit": EXPECTED_SELECTION_COMMIT,
        "protocol_commit": _git(root, "rev-parse", "HEAD"),
        "protocol_sha256": protocol["protocol_sha256"],
        "primary_config_sha256": config["config_sha256"],
        "split_hashes": config["split_hashes"],
        "model": config["model"],
        "model_parameters": config["model_parameters"],
        "representation": config["representation"],
        "feature_count": config["feature_count"],
        "classification_threshold": config["classification_threshold"],
        "software_versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "conditions": condition_outputs,
        "random_minus_geographic_balanced_accuracy": float(random_score - geographic_score),
        "difference_definition": "positive means geographic balanced accuracy was lower",
        "secondary_final_baselines": [],
        "permutation_sanity_reference": {
            "scope": "Phase 2D-A geographic development only",
            "runs": 5,
            "mean_balanced_accuracy": 0.5285714285714286,
            "used_for_final_tuning": False,
        },
        "no_retuning_declaration": True,
        "interpretation_limit": (
            "Curated known bowl-barrow patches versus deterministically sampled unlabelled "
            "background terrain; not unknown-site discovery."
        ),
    }
    audit = {
        "schema_version": "e001-final-model-audit-v1",
        "final_metrics_frozen_before_error_analysis": True,
        "primary_config_sha256": config["config_sha256"],
        "conditions": diagnostic_payloads,
        "privacy": {
            "aggregate_only": True,
            "coordinates_in_output": False,
            "sample_identifiers_in_output": False,
            "maps_created": False,
        },
        "no_post_final_training_or_tuning": True,
    }
    assert_coordinate_safe_mapping(result)
    assert_coordinate_safe_mapping(audit)
    output_root = root / "outputs/modelling"
    with (output_root / "e001_random_vs_geographic.json").open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    _write_csv_exclusive(output_root / "e001_final_results.csv", result)
    with (output_root / "e001_final_model_audit.json").open("x", encoding="utf-8") as handle:
        json.dump(audit, handle, indent=2)
        handle.write("\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Run the pre-registered E001 geographic train/development baseline matrix only."""

from __future__ import annotations

import json
import platform
from collections import Counter
from dataclasses import asdict

import numpy as np
import scipy
import sklearn

from archaeoai.model_data import (
    REPRESENTATION_CONFIGS,
    DevelopmentDataLoader,
    configuration_hash,
    validate_frozen_primary_config,
)
from archaeoai.modelling import (
    MODEL_ORDER,
    REPRESENTATION_ORDER,
    evaluate_development,
    select_primary,
)
from archaeoai.paths import find_project_root
from archaeoai.terrain.privacy import assert_coordinate_safe_mapping

PERMUTATION_SEEDS = (20260830, 20260831, 20260832, 20260833, 20260834)


def _metadata_audit(loader: DevelopmentDataLoader) -> dict[str, object]:
    fields = (
        "provenance_id",
        "survey_year",
        "geographic_block_id",
        "source_resolution_m",
    )
    output: dict[str, object] = {}
    for partition in ("train", "development"):
        rows = loader.allowed_metadata_rows(partition)
        partition_output: dict[str, object] = {}
        for field in fields:
            counts = Counter((str(getattr(row, field)), str(row.class_label)) for row in rows)
            values = sorted({value for value, _label in counts})
            category_counts = {
                value: {
                    "positive_bowl_barrow": counts[(value, "positive_bowl_barrow")],
                    "unlabelled_background": counts[(value, "unlabelled_background")],
                }
                for value in values
            }
            maximum_difference = max(
                abs(item["positive_bowl_barrow"] - item["unlabelled_background"])
                for item in category_counts.values()
            )
            partition_output[field] = {
                "category_counts": category_counts,
                "maximum_absolute_class_count_difference": maximum_difference,
            }
        output[partition] = partition_output
    return output


def _model_parameters(preregistration: dict[str, object], model: str) -> dict[str, object]:
    models = preregistration["models"]
    assert isinstance(models, dict)
    specification = models[model]
    assert isinstance(specification, dict)
    parameters = specification["parameters"]
    assert isinstance(parameters, dict)
    return parameters


def main() -> int:
    root = find_project_root()
    preregistration_path = root / "configs/e001-phase-2d-a-preregistered.json"
    preregistration = json.loads(preregistration_path.read_text(encoding="utf-8"))
    if preregistration.get("created_before_development_scoring") is not True:
        raise ValueError("development scoring requires the committed preregistration")
    loader = DevelopmentDataLoader(root, condition="geographic")
    loaded = {
        representation: {
            partition: loader.load_partition(partition, representation)
            for partition in ("train", "development")
        }
        for representation in REPRESENTATION_ORDER
    }
    results = []
    for model in MODEL_ORDER:
        for representation in REPRESENTATION_ORDER:
            train = loaded[representation]["train"]
            development = loaded[representation]["development"]
            result, _estimator = evaluate_development(
                model,
                representation,
                train.features,
                train.labels,
                development.features,
                development.labels,
            )
            results.append(result)
            print(
                f"model={model} representation={representation} "
                f"balanced_accuracy={result.balanced_accuracy:.6f} "
                f"roc_auc={result.roc_auc:.6f}",
                flush=True,
            )
    selected = select_primary(results)
    selected_train = loaded[selected.representation]["train"]
    selected_development = loaded[selected.representation]["development"]
    permutation_results = []
    for seed in PERMUTATION_SEEDS:
        shuffled = np.random.default_rng(seed).permutation(selected_train.labels)
        result, _estimator = evaluate_development(
            selected.model,
            selected.representation,
            selected_train.features,
            shuffled,
            selected_development.features,
            selected_development.labels,
        )
        permutation_results.append(
            {
                "seed": seed,
                "balanced_accuracy": result.balanced_accuracy,
                "roc_auc": result.roc_auc,
            }
        )
    permutation_summary = {
        "runs": len(permutation_results),
        "mean_balanced_accuracy": float(
            np.mean([row["balanced_accuracy"] for row in permutation_results])
        ),
        "minimum_balanced_accuracy": min(row["balanced_accuracy"] for row in permutation_results),
        "maximum_balanced_accuracy": max(row["balanced_accuracy"] for row in permutation_results),
        "mean_roc_auc": float(np.mean([row["roc_auc"] for row in permutation_results])),
        "selected_score_exceeds_all_permutations": selected.balanced_accuracy
        > max(row["balanced_accuracy"] for row in permutation_results),
        "used_for_selection": False,
    }
    metadata_audit = _metadata_audit(loader)
    manifests = {
        condition: json.loads(
            (root / f"outputs/dataset/e001_{condition}_split_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        for condition in ("random", "geographic")
    }
    result_rows = [asdict(result) for result in results]
    output: dict[str, object] = {
        "phase": "2D-A geographic development-only baseline selection",
        "preregistration": "configs/e001-phase-2d-a-preregistered.json",
        "condition": "geographic",
        "partitions_accessed": ["train", "development"],
        "final_test_accessed": False,
        "random_condition_evaluated": False,
        "counts": {
            "train": len(loaded["normalized_elevation"]["train"].labels),
            "development": len(loaded["normalized_elevation"]["development"].labels),
            "candidates": len(result_rows),
        },
        "results": result_rows,
        "selected": asdict(selected),
        "selection_rule": preregistration["selection"],
        "permutation_sanity_checks": permutation_results,
        "permutation_sanity_summary": permutation_summary,
        "metadata_shortcut_audit": metadata_audit,
        "split_hashes": {
            condition: manifest["assignment_sha256"] for condition, manifest in manifests.items()
        },
        "scope": {
            "final_accuracy_computed": False,
            "final_f1_computed": False,
            "final_roc_auc_computed": False,
            "predictions_inspected": False,
        },
    }
    assert_coordinate_safe_mapping(output)
    output_root = root / "outputs/modelling"
    output_root.mkdir(parents=True, exist_ok=True)
    results_path = output_root / "e001_phase_2d_a_development_results.json"
    results_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")

    selected_channels = REPRESENTATION_CONFIGS[selected.representation]
    primary: dict[str, object] = {
        "schema_version": "e001-primary-baseline-v1",
        "frozen": True,
        "creation_date": "2026-08-29",
        "selection_condition": "geographic",
        "selection_partition": "development",
        "model": selected.model,
        "model_parameters": _model_parameters(preregistration, selected.model),
        "representation": selected.representation,
        "representation_channels": list(selected_channels),
        "feature_count": selected.feature_count,
        "pooling": preregistration["pooling"],
        "standard_scaler": selected.model == "logistic_regression",
        "scaler_fit_scope": "training_only" if selected.model == "logistic_regression" else "none",
        "classification_threshold": 0.5,
        "seeds": {
            "model": 20260829,
            "permutation": list(PERMUTATION_SEEDS),
        },
        "software_versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "split_hashes": output["split_hashes"],
        "selection_rule": preregistration["selection"],
        "development_evidence": asdict(selected),
        "permutation_sanity_checks": permutation_results,
        "permutation_sanity_summary": permutation_summary,
        "final_test_evaluated": False,
        "future_final_evaluation_requires_this_hash": True,
    }
    primary["config_sha256"] = configuration_hash(primary)
    assert_coordinate_safe_mapping(primary)
    primary_path = output_root / "e001_primary_baseline_config.json"
    primary_path.write_text(json.dumps(primary, indent=2) + "\n", encoding="utf-8")
    validate_frozen_primary_config(primary_path)
    print(json.dumps({"selected": primary, "results_path": str(results_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

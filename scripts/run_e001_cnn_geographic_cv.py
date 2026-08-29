"""Run the frozen Phase 2E-B 5-fold × 3-seed compact-CNN experiment once."""

from __future__ import annotations

import csv
import hashlib
import json
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import confusion_matrix

from archaeoai.cnn_training import (
    CLASSIFICATION_THRESHOLD,
    binary_metrics,
    evaluate_frozen_cnn,
    materialize_dataset,
    normalization_mapping,
    synthetic_cpu_inference_ms_per_patch,
    train_frozen_cnn,
    validate_training_contract,
)
from archaeoai.dataset import BACKGROUND_LABEL, POSITIVE_LABEL
from archaeoai.deep_learning import (
    CNN_SEEDS,
    E001TerrainDataset,
    build_fold_partitions,
    fit_training_normalization,
    read_cnn_records,
    read_fold_assignments,
    validate_cnn_protocol,
)
from archaeoai.terrain.privacy import assert_coordinate_safe_mapping, verify_git_ignored

RF_FOLD_BALANCED_ACCURACY = (0.796296, 0.839623, 0.79, 0.861111, 0.83)
RF_MEAN_BALANCED_ACCURACY = 0.823406
IMMUTABLE_ARTIFACTS = {
    "outputs/modelling/e001_final_results.csv": (
        "28b7503965ea75143616f5e726890b842030a20be8c283e2e9a7dd3c540e39a6"
    ),
    "outputs/modelling/e001_random_vs_geographic.json": (
        "6d6d8cf9ebca15d7cf28c99e9d05d9b94b5837695aaf29a973c80d708aad9055"
    ),
    "outputs/modelling/e001_final_model_audit.json": (
        "ad1204c002b6eb591b9ccf8cfdc89021ffcc6f8b709b30aae6fefd0ec9e891c2"
    ),
    "outputs/robustness/e001_robustness_summary.json": (
        "6ebf881562458110562e7181824c677acf7ecfa7edc673152e96bf1a7c319591"
    ),
    "outputs/robustness/e001_geographic_fold_manifest.json": (
        "2575232a392925eedcbabe343e599df58a789137bad3b356b3774e9ef9637157"
    ),
}


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError("refusing to write an empty CNN result table")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _summary(values: list[float]) -> dict[str, float]:
    return {
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "population_standard_deviation": statistics.pstdev(values),
        "minimum": min(values),
        "maximum": max(values),
    }


def _validate_immutable_artifacts(root: Path) -> None:
    for relative_path, expected in IMMUTABLE_ARTIFACTS.items():
        observed = hashlib.sha256((root / relative_path).read_bytes()).hexdigest()
        if observed != expected:
            raise ValueError(f"immutable research artifact changed: {relative_path}")
    fold_manifest = json.loads(
        (root / "outputs/robustness/e001_geographic_fold_manifest.json").read_text()
    )
    integrity = fold_manifest["integrity"]
    if (
        integrity["cross_fold_terrain_window_overlaps"] != 0
        or integrity["matched_and_overlap_units_kept_whole"] is not True
    ):
        raise ValueError("frozen geographic fold leakage audit changed")


def run() -> None:
    root = Path(__file__).resolve().parents[1]
    output_root = root / "outputs/deep_learning"
    result_paths = (
        output_root / "e001_cnn_fold_results.csv",
        output_root / "e001_cnn_seed_summary.csv",
        output_root / "e001_cnn_vs_rf.json",
        output_root / "e001_cnn_summary.json",
        output_root / "e001_cnn_training_history.csv",
        output_root / "e001_cnn_group_summary.csv",
    )
    if any(path.exists() for path in result_paths):
        raise FileExistsError("refusing to overwrite existing E001 CNN results")
    _validate_immutable_artifacts(root)
    protocol = validate_cnn_protocol(output_root / "e001_cnn_protocol.json")
    validate_training_contract(protocol)
    if not torch.cuda.is_available():
        raise RuntimeError("frozen Phase 2E-B primary runs require CUDA")
    if torch.cuda.get_device_name(0) != protocol["hardware_verification"]["gpu_name"]:
        raise RuntimeError("active GPU differs from the frozen protocol environment")
    records = read_cnn_records(root / "outputs/dataset/e001_modelling_index.csv")
    assignments = read_fold_assignments(root / "outputs/robustness/e001_geographic_fold_groups.csv")
    private_root = root / "data/private/e001"
    checkpoint_root = private_root / "deep_learning/checkpoints"
    run_rows: list[dict[str, object]] = []
    history_rows: list[dict[str, object]] = []
    group_values: dict[str, dict[str, list[float] | list[int]]] = defaultdict(
        lambda: {"labels": [], "predictions": [], "scores": []}
    )
    normalization_rows: dict[str, dict[str, list[float] | str]] = {}
    total_started = time.perf_counter()
    first_state = None
    for held_out_fold in range(5):
        partitions = build_fold_partitions(records, assignments, held_out_fold=held_out_fold)
        fold_name = f"fold_{held_out_fold + 1}"
        raw_training = E001TerrainDataset(
            partitions.internal_train,
            private_root=private_root,
            role="internal_train",
        )
        normalization = fit_training_normalization(raw_training)
        normalization_rows[fold_name] = normalization_mapping(normalization)
        training = materialize_dataset(
            E001TerrainDataset(
                partitions.internal_train,
                private_root=private_root,
                role="internal_train",
                normalization=normalization,
            )
        )
        internal_validation = materialize_dataset(
            E001TerrainDataset(
                partitions.internal_validation,
                private_root=private_root,
                role="internal_validation",
                normalization=normalization,
            )
        )
        trained = []
        for seed in CNN_SEEDS:
            checkpoint_path = checkpoint_root / f"{fold_name}_seed_{seed}.pt"
            outcome = train_frozen_cnn(
                training,
                internal_validation,
                seed=seed,
                device="cuda",
                checkpoint_path=checkpoint_path,
                project_root=root,
                protocol_sha256=protocol["protocol_sha256"],
            )
            trained.append(outcome)
            if first_state is None:
                first_state = outcome.state_dict
            history_rows.extend(
                {
                    "fold": fold_name,
                    "seed": seed,
                    "epoch": item.epoch,
                    "training_loss": item.training_loss,
                    "internal_validation_loss": item.internal_validation_loss,
                    "improved": item.improved,
                }
                for item in outcome.history
            )
            print(
                f"trained {fold_name} seed {seed}: epochs={outcome.epochs_trained} "
                f"best_epoch={outcome.best_epoch} "
                f"best_val={outcome.best_internal_validation_loss:.6f}",
                flush=True,
            )
        held_out = materialize_dataset(
            E001TerrainDataset(
                partitions.held_out,
                private_root=private_root,
                role="held_out",
                normalization=normalization,
            )
        )
        held_labels = held_out.tensors[1].numpy().astype(np.int8)
        for outcome in trained:
            evaluation = evaluate_frozen_cnn(
                outcome.state_dict,
                held_out,
                device="cuda",
                seed=outcome.seed,
            )
            counts = Counter(record.class_label for record in partitions.held_out)
            run_rows.append(
                {
                    "fold": fold_name,
                    "seed": outcome.seed,
                    "training_observations": len(partitions.internal_train),
                    "internal_validation_observations": len(partitions.internal_validation),
                    "held_out_observations": len(partitions.held_out),
                    "held_out_positive_bowl_barrow": counts[POSITIVE_LABEL],
                    "held_out_unlabelled_background": counts[BACKGROUND_LABEL],
                    **evaluation.metrics,
                    **evaluation.confusion,
                    "epochs_trained": outcome.epochs_trained,
                    "best_epoch": outcome.best_epoch,
                    "best_internal_validation_loss": outcome.best_internal_validation_loss,
                    "training_seconds": outcome.training_seconds,
                    "inference_seconds": evaluation.inference_seconds,
                    "inference_ms_per_patch": evaluation.inference_ms_per_patch,
                    "peak_gpu_memory_bytes": outcome.peak_gpu_memory_bytes,
                    "model_state_sha256": outcome.state_sha256,
                    "private_checkpoint_sha256": outcome.checkpoint_sha256,
                    "private_checkpoint_size_bytes": outcome.checkpoint_size_bytes,
                    "classification_threshold": CLASSIFICATION_THRESHOLD,
                    "predicted_positive_count": int(evaluation.predictions.sum()),
                }
            )
            for index, record in enumerate(partitions.held_out):
                group = group_values[record.geographic_block_id]
                group["labels"].append(int(held_labels[index]))
                group["predictions"].append(int(evaluation.predictions[index]))
                group["scores"].append(float(evaluation.scores[index]))
            print(
                f"evaluated {fold_name} seed {outcome.seed}: "
                f"balanced_accuracy={evaluation.metrics['balanced_accuracy']:.6f}",
                flush=True,
            )
    total_wall_seconds = time.perf_counter() - total_started
    if len(run_rows) != 15 or first_state is None:
        raise RuntimeError("Phase 2E-B did not complete all 15 frozen runs")

    fold_rows = []
    fold_means = []
    for fold_index in range(5):
        fold_name = f"fold_{fold_index + 1}"
        rows = [row for row in run_rows if row["fold"] == fold_name]
        values = [float(row["balanced_accuracy"]) for row in rows]
        fold_mean = statistics.fmean(values)
        fold_means.append(fold_mean)
        fold_rows.append(
            {
                "fold": fold_name,
                "cnn_mean_balanced_accuracy": fold_mean,
                "cnn_population_standard_deviation": statistics.pstdev(values),
                "rf_balanced_accuracy": RF_FOLD_BALANCED_ACCURACY[fold_index],
                "cnn_minus_rf": fold_mean - RF_FOLD_BALANCED_ACCURACY[fold_index],
            }
        )
    seed_rows = []
    for seed in CNN_SEEDS:
        values = [float(row["balanced_accuracy"]) for row in run_rows if row["seed"] == seed]
        seed_rows.append(
            {
                "seed": seed,
                "mean_balanced_accuracy": statistics.fmean(values),
                "population_standard_deviation": statistics.pstdev(values),
                "minimum": min(values),
                "maximum": max(values),
            }
        )
    seed_means = [float(row["mean_balanced_accuracy"]) for row in seed_rows]
    all_balanced = [float(row["balanced_accuracy"]) for row in run_rows]
    metric_names = (
        "balanced_accuracy",
        "accuracy",
        "precision",
        "recall",
        "f1",
        "roc_auc",
        "average_precision",
    )
    run_metric_summary = {
        name: _summary([float(row[name]) for row in run_rows]) for name in metric_names
    }
    confusion = {name: sum(int(row[name]) for row in run_rows) for name in ("tn", "fp", "fn", "tp")}
    group_rows = []
    for group_name, values in sorted(group_values.items()):
        labels = np.asarray(values["labels"], dtype=np.int8)
        predictions = np.asarray(values["predictions"], dtype=np.int8)
        scores = np.asarray(values["scores"], dtype=np.float64)
        metrics = binary_metrics(labels, predictions, scores)
        tn, fp, fn, tp = (
            int(value) for value in confusion_matrix(labels, predictions, labels=[0, 1]).ravel()
        )
        group_rows.append(
            {
                "geographic_block_id": group_name,
                "evaluations": len(labels),
                "unique_observations": len(labels) // len(CNN_SEEDS),
                **metrics,
                "tn": tn,
                "fp": fp,
                "fn": fn,
                "tp": tp,
            }
        )
    early_stopped = sum(int(row["epochs_trained"]) < 100 for row in run_rows)
    best_epochs = [int(row["best_epoch"]) for row in run_rows]
    final_history = {(row["fold"], row["seed"]): row for row in history_rows}
    class_collapsed_runs = sum(
        int(row["predicted_positive_count"]) in {0, int(row["held_out_observations"])}
        for row in run_rows
    )
    summary = {
        "status": "COMPLETE_UNINTERPRETED",
        "analysis_label": "posthoc_stronger_model_geographic_cv",
        "protocol_sha256": protocol["protocol_sha256"],
        "fold_assignment_sha256": protocol["fold_assignment_sha256"],
        "no_retuning_declaration": True,
        "primary_runs_completed": len(run_rows),
        "fold_mean_balanced_accuracy": _summary(fold_means),
        "all_run_balanced_accuracy": _summary(all_balanced),
        "run_metric_summary": run_metric_summary,
        "aggregate_confusion_across_15_runs": confusion,
        "seed_mean_balanced_accuracy": seed_rows,
        "seed_mean_range": max(seed_means) - min(seed_means),
        "random_forest_reference": {
            "fold_balanced_accuracy": list(RF_FOLD_BALANCED_ACCURACY),
            "mean_balanced_accuracy": RF_MEAN_BALANCED_ACCURACY,
            "descriptive_posthoc_comparison_only": True,
        },
        "cnn_minus_random_forest_mean": statistics.fmean(fold_means) - RF_MEAN_BALANCED_ACCURACY,
        "fold_comparison": fold_rows,
        "training_diagnostics": {
            "early_stopped_runs": early_stopped,
            "maximum_epoch_runs": len(run_rows) - early_stopped,
            "best_epoch_median": statistics.median(best_epochs),
            "best_epoch_minimum": min(best_epochs),
            "best_epoch_maximum": max(best_epochs),
            "initial_training_loss_mean": statistics.fmean(
                float(row["training_loss"]) for row in history_rows if row["epoch"] == 1
            ),
            "final_training_loss_mean": statistics.fmean(
                float(row["training_loss"]) for row in final_history.values()
            ),
            "initial_validation_loss_mean": statistics.fmean(
                float(row["internal_validation_loss"]) for row in history_rows if row["epoch"] == 1
            ),
            "best_validation_loss_mean": statistics.fmean(
                float(row["best_internal_validation_loss"]) for row in run_rows
            ),
            "final_validation_loss_mean": statistics.fmean(
                float(row["internal_validation_loss"]) for row in final_history.values()
            ),
            "class_collapsed_runs": class_collapsed_runs,
        },
        "compute": {
            "gpu": torch.cuda.get_device_name(0),
            "torch": torch.__version__,
            "torch_cuda_runtime": torch.version.cuda,
            "total_gpu_training_seconds": sum(float(row["training_seconds"]) for row in run_rows),
            "total_wall_seconds": total_wall_seconds,
            "mean_training_seconds_per_run": statistics.fmean(
                float(row["training_seconds"]) for row in run_rows
            ),
            "mean_inference_ms_per_patch": statistics.fmean(
                float(row["inference_ms_per_patch"]) for row in run_rows
            ),
            "synthetic_cpu_inference_ms_per_patch": synthetic_cpu_inference_ms_per_patch(
                first_state
            ),
            "median_private_checkpoint_size_bytes": statistics.median(
                int(row["private_checkpoint_size_bytes"]) for row in run_rows
            ),
            "maximum_peak_gpu_memory_bytes": max(
                int(row["peak_gpu_memory_bytes"]) for row in run_rows
            ),
        },
        "normalization_by_fold": normalization_rows,
        "privacy": {
            "coordinates_written": False,
            "sample_identifiers_written": False,
            "sample_predictions_written": False,
            "checkpoints_private_and_ignored": True,
            "maps_created": False,
        },
        "stronger_model_classification": None,
        "phase_2f_recommendation": None,
    }
    comparison = {
        "analysis_label": summary["analysis_label"],
        "protocol_sha256": protocol["protocol_sha256"],
        "fold_assignment_sha256": protocol["fold_assignment_sha256"],
        "folds": fold_rows,
        "cnn_mean_balanced_accuracy": statistics.fmean(fold_means),
        "rf_mean_balanced_accuracy": RF_MEAN_BALANCED_ACCURACY,
        "cnn_minus_rf": statistics.fmean(fold_means) - RF_MEAN_BALANCED_ACCURACY,
        "descriptive_posthoc_comparison_only": True,
        "statistical_significance_claimed": False,
    }
    assert_coordinate_safe_mapping(summary)
    assert_coordinate_safe_mapping(comparison)
    output_root.mkdir(parents=True, exist_ok=True)
    _write_csv(output_root / "e001_cnn_fold_results.csv", run_rows)
    _write_csv(output_root / "e001_cnn_seed_summary.csv", seed_rows)
    _write_csv(output_root / "e001_cnn_training_history.csv", history_rows)
    _write_csv(output_root / "e001_cnn_group_summary.csv", group_rows)
    (output_root / "e001_cnn_vs_rf.json").write_text(
        json.dumps(comparison, indent=2) + "\n", encoding="utf-8"
    )
    (output_root / "e001_cnn_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"completed 15 frozen runs: fold-mean BA={statistics.fmean(fold_means):.6f}",
        flush=True,
    )


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    try:
        run()
    except Exception as error:
        failure_path = root / "data/private/e001/deep_learning/training_failure.json"
        failure_path.parent.mkdir(parents=True, exist_ok=True)
        verify_git_ignored(root, failure_path)
        failure_path.write_text(
            json.dumps(
                {
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "scientific_hyperparameters_changed": False,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        raise


if __name__ == "__main__":
    main()

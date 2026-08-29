"""Hash-bound, one-way E001 final evaluation utilities."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

from archaeoai.dataset import BACKGROUND_LABEL, POSITIVE_LABEL
from archaeoai.model_data import (
    DevelopmentDataLoader,
    LoadedPartition,
    configuration_hash,
    mean_pool_4x4,
    validate_frozen_primary_config,
)
from archaeoai.modelling import build_estimator
from archaeoai.terrain.full_dataset import load_processed_archive, terrain_content_digest

EXPECTED_SELECTION_COMMIT = "790ac9f4b99da94e8f9bab2a6aed70b34ac88558"
EXPECTED_CONFIG_SHA256 = "20cd377c17373eeeb5403c84119084287f193d93b42c8004d99c823e01a157e4"
FINAL_CONDITIONS = ("random", "geographic")
FINAL_METRICS = (
    "balanced_accuracy",
    "accuracy",
    "precision",
    "recall",
    "f1",
    "roc_auc",
    "average_precision",
    "confusion_matrix",
)


@dataclass(frozen=True, slots=True)
class FinalIndexRow:
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
    def bootstrap_group_id(self) -> str:
        return self.overlap_component_id or self.observation_group_id


@dataclass(frozen=True, slots=True)
class LoadedFinalPartition:
    features: np.ndarray
    labels: np.ndarray
    rows: tuple[FinalIndexRow, ...]
    terrain_summaries: tuple[dict[str, float], ...]


def protocol_hash(payload: dict[str, Any]) -> str:
    content = {key: value for key, value in payload.items() if key != "protocol_sha256"}
    encoded = json.dumps(content, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def validate_final_protocol(
    protocol_path: Path, primary_config_path: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    expected_protocol_hash = protocol.get("protocol_sha256")
    if (
        not isinstance(expected_protocol_hash, str)
        or protocol_hash(protocol) != expected_protocol_hash
    ):
        raise ValueError("final-evaluation protocol hash mismatch")
    if (
        protocol.get("frozen") is not True
        or protocol.get("created_before_final_test_scoring") is not True
    ):
        raise ValueError("final-evaluation protocol is not frozen before scoring")
    config = validate_frozen_primary_config(primary_config_path)
    if config["config_sha256"] != EXPECTED_CONFIG_SHA256:
        raise ValueError("unexpected primary-configuration hash")
    if protocol.get("primary_config_sha256") != config["config_sha256"]:
        raise ValueError("protocol does not bind the primary configuration")
    if protocol.get("selection_commit") != EXPECTED_SELECTION_COMMIT:
        raise ValueError("protocol does not bind the selection commit")
    for key in (
        "model",
        "model_parameters",
        "representation",
        "representation_channels",
        "pooling",
        "feature_count",
        "classification_threshold",
        "split_hashes",
    ):
        if protocol.get(key) != config.get(key):
            raise ValueError(f"protocol and primary configuration differ for {key}")
    if tuple(protocol.get("condition_order", ())) != FINAL_CONDITIONS:
        raise ValueError("final conditions or their order changed")
    if tuple(protocol.get("metrics", ())) != FINAL_METRICS:
        raise ValueError("final metrics changed")
    if protocol.get("secondary_final_baselines") != []:
        raise ValueError("secondary final baselines were not pre-registered")
    if config.get("final_test_evaluated") is not False:
        raise ValueError("primary configuration does not preserve the pre-unlock state")
    return protocol, config


def validate_final_split(root: Path, condition: str, expected_hash: str) -> dict[str, Any]:
    if condition not in FINAL_CONDITIONS:
        raise ValueError("unsupported final condition")
    manifest_path = root / f"outputs/dataset/e001_{condition}_split_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("frozen") is not True or manifest.get("assignment_sha256") != expected_hash:
        raise ValueError("final split manifest differs from the frozen configuration")
    digest = hashlib.sha256()
    with (root / "outputs/dataset/e001_modelling_index.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        rows = sorted(csv.DictReader(handle), key=lambda row: row["sample_id"])
    for row in rows:
        digest.update(f"{row['sample_id']}:{row['split_' + condition]}\n".encode())
    if digest.hexdigest() != expected_hash:
        raise ValueError("final split assignment hash mismatch")
    return manifest


def _private_archive(root: Path, row: FinalIndexRow) -> Path:
    if row.class_label == POSITIVE_LABEL:
        subdirectory = "terrain/processed"
    elif row.class_label == BACKGROUND_LABEL:
        subdirectory = "backgrounds/processed"
    else:
        raise ValueError("final label must come from the safe modelling index")
    return root / "data/private/e001" / subdirectory / f"{row.sample_id}.npz"


def load_final_partition(
    root: Path,
    *,
    condition: str,
    expected_split_hash: str,
) -> LoadedFinalPartition:
    """Load one hash-authorized final partition using only frozen terrain features."""
    validate_final_split(root, condition, expected_split_hash)
    with (root / "outputs/dataset/e001_modelling_index.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        source_rows = sorted(csv.DictReader(handle), key=lambda row: row["sample_id"])
    selected = [row for row in source_rows if row[f"split_{condition}"] == "final_test"]
    rows = tuple(
        FinalIndexRow(
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
        for row in selected
    )
    features = []
    labels = []
    terrain_summaries = []
    for row in rows:
        if row.qa_status != "pass":
            raise ValueError("final evaluation requires QA-passed terrain")
        elevation, mask, representations = load_processed_archive(_private_archive(root, row))
        if terrain_content_digest(elevation, mask) != row.patch_sha256:
            raise ValueError("final terrain content checksum mismatch")
        features.append(
            np.concatenate(
                [
                    mean_pool_4x4(representations[channel])
                    for channel in (
                        "elevation_normalized",
                        "slope_degrees",
                        "hillshade_315_45",
                        "local_relief_r16m",
                    )
                ]
            )
        )
        labels.append(1 if row.class_label == POSITIVE_LABEL else 0)
        terrain_summaries.append(
            {
                "median_absolute_elevation_m": float(np.nanmedian(elevation)),
                "mean_slope_degrees": float(np.nanmean(representations["slope_degrees"])),
                "mean_absolute_local_relief_m": float(
                    np.nanmean(np.abs(representations["local_relief_r16m"]))
                ),
                "missing_fraction": float(1.0 - np.mean(mask)),
            }
        )
    matrix = np.asarray(features, dtype=np.float32)
    if matrix.shape != (62, 4096) or not np.isfinite(matrix).all():
        raise ValueError("final feature matrix does not match the frozen design")
    label_array = np.asarray(labels, dtype=np.int8)
    if np.bincount(label_array, minlength=2).tolist() != [31, 31]:
        raise ValueError("final class counts do not match the frozen design")
    return LoadedFinalPartition(matrix, label_array, rows, tuple(terrain_summaries))


def load_final_training_partition(root: Path, condition: str) -> LoadedPartition:
    partition = DevelopmentDataLoader(root, condition=condition).load_partition("train", "all_four")
    if partition.features.shape != (432, 4096):
        raise ValueError("training feature matrix does not match the frozen design")
    if np.bincount(partition.labels, minlength=2).tolist() != [216, 216]:
        raise ValueError("training class counts do not match the frozen design")
    return partition


def metric_values(
    labels: np.ndarray, predictions: np.ndarray, probabilities: np.ndarray
) -> dict[str, Any]:
    tn, fp, fn, tp = confusion_matrix(labels, predictions, labels=[0, 1]).ravel()
    return {
        "balanced_accuracy": float(balanced_accuracy_score(labels, predictions)),
        "accuracy": float(accuracy_score(labels, predictions)),
        "precision": float(precision_score(labels, predictions, zero_division=0)),
        "recall": float(recall_score(labels, predictions, zero_division=0)),
        "f1": float(f1_score(labels, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(labels, probabilities)),
        "average_precision": float(average_precision_score(labels, probabilities)),
        "confusion_matrix": {
            "true_unlabelled_background_predicted_unlabelled_background": int(tn),
            "true_unlabelled_background_predicted_positive_bowl_barrow": int(fp),
            "true_positive_bowl_barrow_predicted_unlabelled_background": int(fn),
            "true_positive_bowl_barrow_predicted_positive_bowl_barrow": int(tp),
        },
    }


def fit_and_evaluate(
    training: LoadedPartition,
    final: LoadedFinalPartition,
    *,
    threshold: float,
) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    estimator = build_estimator("random_forest")
    estimator.fit(training.features, training.labels)
    probabilities = estimator.predict_proba(final.features)[:, 1]
    predictions = (probabilities >= threshold).astype(np.int8)
    return metric_values(final.labels, predictions, probabilities), predictions, probabilities


def group_bootstrap_intervals(
    final: LoadedFinalPartition,
    predictions: np.ndarray,
    probabilities: np.ndarray,
    *,
    iterations: int,
    seed: int,
) -> dict[str, Any]:
    grouped: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(final.rows):
        grouped[row.bootstrap_group_id].append(index)
    units = sorted(grouped)
    rng = np.random.default_rng(seed)
    collected = {name: [] for name in ("balanced_accuracy", "accuracy", "f1", "roc_auc")}
    undefined = {name: 0 for name in collected}
    for _iteration in range(iterations):
        sampled_units = rng.choice(units, size=len(units), replace=True)
        indices = np.asarray([index for unit in sampled_units for index in grouped[str(unit)]])
        labels = final.labels[indices]
        sampled_predictions = predictions[indices]
        sampled_probabilities = probabilities[indices]
        values = {
            "balanced_accuracy": balanced_accuracy_score(labels, sampled_predictions),
            "accuracy": accuracy_score(labels, sampled_predictions),
            "f1": f1_score(labels, sampled_predictions, zero_division=0),
        }
        if len(np.unique(labels)) == 2:
            values["roc_auc"] = roc_auc_score(labels, sampled_probabilities)
        else:
            values["roc_auc"] = float("nan")
        for name, value in values.items():
            if np.isfinite(value):
                collected[name].append(float(value))
            else:
                undefined[name] += 1
    output = {}
    for name, values in collected.items():
        if not values:
            output[name] = {
                "lower": None,
                "upper": None,
                "valid_replicates": 0,
                "undefined_replicates": undefined[name],
            }
            continue
        lower, upper = np.percentile(np.asarray(values), [2.5, 97.5])
        output[name] = {
            "lower": float(lower),
            "upper": float(upper),
            "valid_replicates": len(values),
            "undefined_replicates": undefined[name],
        }
    return {
        "method": "group_percentile_bootstrap",
        "confidence_level": 0.95,
        "iterations": iterations,
        "seed": seed,
        "unit_count": len(units),
        "unit": "overlap_component_id_else_observation_group_id",
        "intervals": output,
    }


def curve_values(labels: np.ndarray, probabilities: np.ndarray) -> dict[str, list[list[float]]]:
    false_positive_rate, true_positive_rate, _roc_thresholds = roc_curve(labels, probabilities)
    precision, recall, _pr_thresholds = precision_recall_curve(labels, probabilities)
    return {
        "roc": [
            [float(x), float(y)]
            for x, y in zip(false_positive_rate, true_positive_rate, strict=True)
        ],
        "precision_recall": [[float(x), float(y)] for x, y in zip(recall, precision, strict=True)],
    }


def configuration_is_unchanged(config: dict[str, Any]) -> bool:
    return configuration_hash(config) == EXPECTED_CONFIG_SHA256

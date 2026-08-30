"""Immutable aggregate validation for the spent E001 Phase 3C external test."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from archaeoai.external_validation import (
    classify_external_result,
    paired_cluster_bootstrap_indices,
)
from archaeoai.terrain.privacy import assert_coordinate_safe_mapping

EXPECTED_DATASET_SHA256 = "17eeb9366e02ce2acddcfaf3324a9558a439a5655139859e6f9fb0707f69057c"
EXPECTED_PROTOCOL_SHA256 = "ebc3d112c7b101881798d1f62c740a6634275c7834d7c7f53b330fe0f5dd84ba"
EXPECTED_AMENDMENT_SHA256 = "330263472d6b947fa688cbe6a21a52f437fc7c206555a023b7e64900c7bf13f9"
EXPECTED_RF_CONFIG_SHA256 = "20cd377c17373eeeb5403c84119084287f193d93b42c8004d99c823e01a157e4"
EXPECTED_MODEL_STATE_SHA256 = "e3b0c072f437e889f09a2a2cf5a37f19b2f483eb5188e102b132a89ee76d1939"
EXPECTED_MODEL_ARTIFACT_SHA256 = "50f7968069ecaa1e0016f37be6356531ab3f26802c806efb5dc8fb2e295a503f"
EXPECTED_PREDICTION_VECTOR_SHA256 = (
    "bd4a14794132b57f19b8345f70f2f1259f5d385a06ee2328d02bcab9d8b91ca7"
)
EXPECTED_AUTHORIZATION_SHA256 = "7ece535dc88810028538082f393c9e89a502dffffb2a3990d2d014725a17dd54"


def canonical_sha256(payload: Any, *, omit: str | None = None) -> str:
    """Hash a JSON-compatible value using the project's canonical encoding."""
    content = payload
    if omit is not None:
        content = {key: value for key, value in payload.items() if key != omit}
    encoded = json.dumps(content, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def result_sha256(payload: Mapping[str, Any]) -> str:
    """Hash the coordinate-safe public result without its self digest."""
    return canonical_sha256(dict(payload), omit="result_sha256")


def validate_external_evaluation_result(path: str | Path) -> dict[str, Any]:
    """Validate the frozen aggregate Phase 3C result and spent-test boundary."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    assert_coordinate_safe_mapping(payload)
    if payload.get("schema_version") != "e001-phase-3c-external-evaluation-v1":
        raise ValueError("unexpected Phase 3C result schema")
    if payload.get("status") != "EXTERNAL_EVALUATION_COMPLETE":
        raise ValueError("Phase 3C evaluation is not complete")
    if payload.get("external_test_spent") is not True or payload.get("frozen") is not True:
        raise ValueError("Phase 3C external test is not frozen and spent")
    if result_sha256(payload) != payload.get("result_sha256"):
        raise ValueError("Phase 3C public result hash mismatch")
    expected_bindings = {
        "dataset_sha256": EXPECTED_DATASET_SHA256,
        "protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "amendment_sha256": EXPECTED_AMENDMENT_SHA256,
        "rf_config_sha256": EXPECTED_RF_CONFIG_SHA256,
        "model_state_sha256": EXPECTED_MODEL_STATE_SHA256,
        "model_artifact_sha256": EXPECTED_MODEL_ARTIFACT_SHA256,
        "prediction_vector_sha256": EXPECTED_PREDICTION_VECTOR_SHA256,
        "authorization_receipt_sha256": EXPECTED_AUTHORIZATION_SHA256,
    }
    if any(payload.get(key) != value for key, value in expected_bindings.items()):
        raise ValueError("Phase 3C frozen binding changed")
    if payload.get("counts") != {
        "positive_bowl_barrow": 60,
        "unlabelled_background": 60,
        "total_observations": 120,
        "matched_pairs": 60,
    }:
        raise ValueError("Phase 3C evaluation counts changed")
    pipeline = payload.get("pipeline", {})
    if (
        pipeline.get("feature_count") != 4096
        or pipeline.get("classification_threshold") != 0.5
        or pipeline.get("model_retrained") is not False
        or pipeline.get("model_retuned") is not False
        or pipeline.get("external_observations_removed_or_replaced_after_scoring") is not False
        or pipeline.get("second_external_scoring_run") is not False
    ):
        raise ValueError("Phase 3C pipeline, no-retuning, or one-run boundary changed")
    primary = payload.get("primary", {})
    metrics = primary.get("metrics", {})
    if primary.get("metric") != "balanced_accuracy":
        raise ValueError("Phase 3C primary metric changed")
    if metrics.get("confusion_matrix") != {"tn": 52, "fp": 8, "fn": 11, "tp": 49}:
        raise ValueError("Phase 3C confusion matrix changed")
    interval = primary.get("confidence_interval", {})
    if (
        interval.get("replicates") != 10_000
        or interval.get("seed") != 20260830
        or interval.get("lower_95") != 0.775
        or interval.get("upper_95") != 0.9
    ):
        raise ValueError("Phase 3C confidence interval changed")
    if primary.get("outcome_classification") != "EXTERNAL_GENERALIZATION_SUPPORTED":
        raise ValueError("Phase 3C outcome classification changed")
    privacy = payload.get("privacy", {})
    if privacy != {
        "aggregate_only": True,
        "coordinates_written": False,
        "sample_identifiers_written": False,
        "private_prediction_rows_tracked": False,
        "raw_or_processed_terrain_tracked": False,
    }:
        raise ValueError("Phase 3C privacy declaration changed")
    return payload


def metric_payload(
    labels: np.ndarray, predictions: np.ndarray, scores: np.ndarray
) -> dict[str, Any]:
    """Reproduce the frozen preregistered metrics from a private prediction vector."""
    target = np.asarray(labels, dtype=np.int8)
    predicted = np.asarray(predictions, dtype=np.int8)
    values = np.asarray(scores, dtype=np.float64)
    if target.shape != predicted.shape or target.shape != values.shape or target.shape != (120,):
        raise ValueError("Phase 3C reproduction requires exactly 120 aligned predictions")
    if np.bincount(target, minlength=2).tolist() != [60, 60]:
        raise ValueError("Phase 3C reproduction requires the frozen 60/60 class balance")
    tn, fp, fn, tp = confusion_matrix(target, predicted, labels=[0, 1]).ravel()
    return {
        "balanced_accuracy": float((tp / (tp + fn) + tn / (tn + fp)) / 2),
        "accuracy": float(accuracy_score(target, predicted)),
        "precision": float(precision_score(target, predicted, zero_division=0)),
        "recall": float(recall_score(target, predicted, zero_division=0)),
        "f1": float(f1_score(target, predicted, zero_division=0)),
        "roc_auc": float(roc_auc_score(target, values)),
        "average_precision": float(average_precision_score(target, values)),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "positive_recall": float(tp / (tp + fn)),
        "unlabelled_background_recall": float(tn / (tn + fp)),
    }


def paired_balanced_accuracy_interval(
    rows: list[Mapping[str, Any]],
) -> dict[str, float | int | str]:
    """Reproduce the exact frozen 10,000-pair bootstrap interval."""
    by_pair: dict[str, dict[int, int]] = {}
    for row in rows:
        by_pair.setdefault(str(row["pair_id"]), {})[int(row["label"])] = int(row["prediction"])
    if len(by_pair) != 60 or any(set(pair) != {0, 1} for pair in by_pair.values()):
        raise ValueError("Phase 3C bootstrap requires 60 complete matched pairs")
    ordered = sorted(by_pair)
    positives = np.asarray([by_pair[pair][1] for pair in ordered])
    backgrounds = np.asarray([by_pair[pair][0] for pair in ordered])
    indices = paired_cluster_bootstrap_indices(60)
    samples = 0.5 * (positives[indices].mean(axis=1) + (1 - backgrounds[indices]).mean(axis=1))
    lower, upper = np.percentile(samples, [2.5, 97.5])
    return {
        "metric": "balanced_accuracy",
        "method": "nonparametric_matched_pair_cluster_bootstrap",
        "replicates": 10_000,
        "seed": 20260830,
        "lower_95": float(lower),
        "upper_95": float(upper),
    }


def reproduce_from_private_predictions(
    private_prediction_path: str | Path, public_result_path: str | Path
) -> None:
    """Verify the private vector against every frozen public aggregate."""
    private = json.loads(Path(private_prediction_path).read_text(encoding="utf-8"))
    public = validate_external_evaluation_result(public_result_path)
    rows = private.get("rows", [])
    if canonical_sha256(rows) != EXPECTED_PREDICTION_VECTOR_SHA256:
        raise ValueError("Phase 3C private prediction-vector checksum mismatch")
    labels = np.asarray(
        [1 if row["class_label"] == "positive_bowl_barrow" else 0 for row in rows],
        dtype=np.int8,
    )
    predictions = np.asarray([row["prediction"] for row in rows], dtype=np.int8)
    scores = np.asarray([row["score"] for row in rows], dtype=np.float64)
    if metric_payload(labels, predictions, scores) != public["primary"]["metrics"]:
        raise ValueError("Phase 3C public metrics do not reproduce from private predictions")
    pair_rows = [
        {"pair_id": row["pair_id"], "label": int(label), "prediction": row["prediction"]}
        for row, label in zip(rows, labels, strict=True)
    ]
    interval = paired_balanced_accuracy_interval(pair_rows)
    if interval != public["primary"]["confidence_interval"]:
        raise ValueError("Phase 3C confidence interval does not reproduce")
    outcome = classify_external_result(
        public["primary"]["metrics"]["balanced_accuracy"],
        interval["lower_95"],
        interval["upper_95"],
        pair_count=60,
    )
    if outcome != public["primary"]["outcome_classification"]:
        raise ValueError("Phase 3C outcome classification does not reproduce")


def assert_external_test_spent(public_result_path: str | Path) -> None:
    """Hard guard used by any future scoring entry point."""
    validate_external_evaluation_result(public_result_path)
    raise FileExistsError("Phase 3C external test is spent; a second scoring run is prohibited")

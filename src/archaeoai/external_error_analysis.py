"""Validation boundary for the frozen, post-hoc E001 Phase 4A analysis."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from archaeoai.external_evaluation import (
    EXPECTED_DATASET_SHA256,
    EXPECTED_MODEL_STATE_SHA256,
    EXPECTED_PREDICTION_VECTOR_SHA256,
    canonical_sha256,
    validate_external_evaluation_result,
)
from archaeoai.terrain.privacy import assert_coordinate_safe_mapping

EXPECTED_PHASE3C_RESULT_SHA256 = "2654932891aa48f4e41ea7cfa8a0f72d5fbbb38a6c2741ce82685fc84edb432b"
EXPECTED_ANALYSIS_SHA256 = "209559c7759c6641d6ac7afeb47bd9a64f3f9581c6a3f9b5d8a5e024825a7276"
EXPECTED_ERROR_GROUPS = {"FN": 11, "FP": 8, "TN": 52, "TP": 49}
EXPECTED_FIGURES = {
    "outputs/external_validation/figures/e001_phase3c_confusion_matrix.svg": (
        "982cdb95de7680202d2eae4b60c2f44ad07953c125bf2f16bce7e0dd82740587"
    ),
    "outputs/external_validation/figures/e001_phase3c_performance_context.svg": (
        "867e788961f19698b594a9d674ba3dfe9e03a8178c75321569d771804cbd32d0"
    ),
    "outputs/external_validation/figures/e001_phase3c_roc_pr_curves.svg": (
        "c2eecdf3ae88428117b21623354493a4675013d0d4e3b0cc28f14bbc4ae85b94"
    ),
    "outputs/external_validation/figures/e001_phase4a_error_representation_summary.svg": (
        "c9bfea220f91c7f255a06473a475e1343d569712abddaabb8a947758dd3cbc8d"
    ),
    "outputs/external_validation/figures/e001_phase4a_score_distributions.svg": (
        "672ff46408ec8aa01abb71fa6d2f34f767cd4f1488a43ed16cf530e33c90fc35"
    ),
}


def analysis_sha256(payload: Mapping[str, Any]) -> str:
    """Hash a Phase 4A result without its self-digest."""
    return canonical_sha256(dict(payload), omit="analysis_sha256")


def validate_external_error_analysis(path: str | Path) -> dict[str, Any]:
    """Validate the immutable coordinate-safe Phase 4A aggregate result."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    assert_coordinate_safe_mapping(payload)
    if payload.get("schema_version") != "e001-phase-4a-external-error-analysis-v1":
        raise ValueError("unexpected Phase 4A result schema")
    if payload.get("status") != "COMPLETE_EXPLORATORY":
        raise ValueError("Phase 4A analysis is not complete")
    if payload.get("analysis_label") != "POST-HOC / EXPLORATORY":
        raise ValueError("Phase 4A must remain explicitly post-hoc and exploratory")
    if payload.get("confirmatory_result_unchanged") is not True:
        raise ValueError("Phase 3C confirmatory result boundary changed")
    if payload.get("external_test_spent") is not True:
        raise ValueError("external-test spent boundary changed")
    if analysis_sha256(payload) != payload.get("analysis_sha256"):
        raise ValueError("Phase 4A aggregate hash mismatch")
    if payload.get("analysis_sha256") != EXPECTED_ANALYSIS_SHA256:
        raise ValueError("Phase 4A frozen aggregate changed")

    bindings = payload.get("source_bindings", {})
    expected_bindings = {
        "phase3c_result_sha256": EXPECTED_PHASE3C_RESULT_SHA256,
        "dataset_sha256": EXPECTED_DATASET_SHA256,
        "model_state_sha256": EXPECTED_MODEL_STATE_SHA256,
        "prediction_vector_sha256": EXPECTED_PREDICTION_VECTOR_SHA256,
        "phase3c_balanced_accuracy": 0.8416666666666667,
        "phase3c_lower_95": 0.775,
        "phase3c_upper_95": 0.9,
    }
    if bindings != expected_bindings:
        raise ValueError("Phase 4A source binding changed")
    if payload.get("error_groups") != EXPECTED_ERROR_GROUPS:
        raise ValueError("Phase 4A confusion groups changed")
    if payload.get("figures") != EXPECTED_FIGURES:
        raise ValueError("Phase 4A figure manifest changed")
    if not 3 <= len(payload.get("hypotheses", [])) <= 6:
        raise ValueError("Phase 4A must retain three to six future hypotheses")
    if (
        payload.get("provenance_descriptive_results", {}).get("causal_interpretation_allowed")
        is not False
    ):
        raise ValueError("Phase 4A provenance analysis cannot be causal")

    science = payload.get("scientific_status", {})
    expected_science = {
        "preferred_current_model": "frozen E001 Random Forest",
        "phase3_external_data_used_for_current_model_training": False,
        "future_model_using_phase3_data_is_new_model_generation": True,
        "new_independent_evaluation_required_for_future_model": True,
        "retraining_performed": False,
        "rescoring_performed": False,
        "threshold_changed": False,
        "observations_removed_or_relabelled": False,
    }
    if science != expected_science:
        raise ValueError("Phase 4A no-change scientific boundary changed")
    expected_privacy = {
        "aggregate_only": True,
        "coordinates_written": False,
        "sample_identifiers_written": False,
        "private_prediction_rows_written": False,
        "maps_created": False,
        "private_panels_tracked": False,
    }
    if payload.get("privacy") != expected_privacy:
        raise ValueError("Phase 4A privacy declaration changed")
    return payload


def verify_phase4a_figure_files(root: str | Path, payload: Mapping[str, Any]) -> None:
    """Verify every frozen public figure byte-for-byte and reject sensitive SVG text."""
    base = Path(root)
    prohibited = (
        "easting",
        "northing",
        "latitude",
        "longitude",
        "sample_id",
        "pair_id",
        "heritage_id",
        "data/private",
        ".npz",
        "<metadata",
    )
    for relative, expected in payload["figures"].items():
        figure = base / relative
        if hashlib.sha256(figure.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Phase 4A figure hash mismatch: {relative}")
        text = figure.read_text(encoding="utf-8").lower()
        if any(token in text for token in prohibited):
            raise ValueError(f"sensitive text in Phase 4A figure: {relative}")


def verify_phase3c_unchanged(root: str | Path, payload: Mapping[str, Any]) -> None:
    """Revalidate that Phase 4A did not alter the spent confirmatory result."""
    result = validate_external_evaluation_result(
        Path(root) / "outputs/external_validation/e001_phase3c_external_evaluation.json"
    )
    if result["result_sha256"] != payload["source_bindings"]["phase3c_result_sha256"]:
        raise ValueError("Phase 3C result changed after the post-hoc analysis")

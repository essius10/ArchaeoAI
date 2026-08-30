"""Hash and validation helpers for the coordinate-safe E001 manuscript package."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from archaeoai.external_error_analysis import EXPECTED_ANALYSIS_SHA256
from archaeoai.external_evaluation import (
    EXPECTED_DATASET_SHA256,
    EXPECTED_MODEL_STATE_SHA256,
    EXPECTED_PREDICTION_VECTOR_SHA256,
)
from archaeoai.terrain.privacy import assert_coordinate_safe_mapping

EXPECTED_PHASE3C_RESULT_SHA256 = "2654932891aa48f4e41ea7cfa8a0f72d5fbbb38a6c2741ce82685fc84edb432b"
EXPECTED_RF_CONFIG_SHA256 = "20cd377c17373eeeb5403c84119084287f193d93b42c8004d99c823e01a157e4"
EXPECTED_MANUSCRIPT_EVIDENCE_SHA256 = (
    "7c9f3c237ce03a33fe7aac91ebd06ce0762f1d93719c28ff077041b90dcc3775"
)
EXPECTED_FIGURE_PATHS = {
    "outputs/deep_learning/figures/e001_cnn_vs_rf_by_fold.svg",
    "outputs/modelling/figures/e001_balanced_accuracy_comparison.svg",
    "outputs/external_validation/figures/e001_phase3c_performance_context.svg",
    "outputs/external_validation/figures/e001_phase3c_confusion_matrix.svg",
    "outputs/external_validation/figures/e001_phase3c_roc_pr_curves.svg",
    "outputs/external_validation/figures/e001_phase4a_score_distributions.svg",
    "outputs/external_validation/figures/e001_phase4a_error_representation_summary.svg",
}
MANUSCRIPT_PATH = "docs/manuscript/archaeoai-e001-manuscript.md"


def repository_sha256(path: str | Path) -> str:
    """Hash a text/binary artifact in its LF-normalized repository form."""
    content = Path(path).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(content).hexdigest()


def canonical_sha256(payload: Mapping[str, Any], *, omit: str | None = None) -> str:
    """Hash JSON-compatible content with stable key ordering."""
    content = dict(payload)
    if omit is not None:
        content.pop(omit, None)
    encoded = json.dumps(content, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def manuscript_word_count(text: str) -> int:
    """Return a stable whitespace-token word count for the Markdown manuscript."""
    return len(re.findall(r"\S+", text))


def manuscript_figure_paths(text: str) -> set[str]:
    """Resolve manuscript image links to repository-relative paths."""
    links = re.findall(r"!\[[^]]*\]\(([^)]+)\)", text)
    resolved: set[str] = set()
    manuscript_parent = Path(MANUSCRIPT_PATH).parent
    for link in links:
        path = (manuscript_parent / link).as_posix()
        while "/../" in path:
            path = re.sub(r"[^/]+/\.\./", "", path, count=1)
        resolved.add(path.removeprefix("./"))
    return resolved


def validate_manuscript_evidence(path: str | Path, *, root: str | Path) -> dict[str, Any]:
    """Validate the manuscript's frozen scientific and file bindings."""
    base = Path(root)
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    assert_coordinate_safe_mapping(payload)
    if payload.get("schema_version") != "e001-phase-4b-manuscript-evidence-v1":
        raise ValueError("unexpected manuscript evidence schema")
    if payload.get("status") != "READY_FOR_REVIEW":
        raise ValueError("manuscript package is not ready for review")
    if canonical_sha256(payload, omit="evidence_manifest_sha256") != payload.get(
        "evidence_manifest_sha256"
    ):
        raise ValueError("manuscript evidence manifest hash mismatch")
    if payload["evidence_manifest_sha256"] != EXPECTED_MANUSCRIPT_EVIDENCE_SHA256:
        raise ValueError("unexpected frozen manuscript evidence SHA-256")
    manuscript = payload.get("manuscript", {})
    manuscript_path = base / manuscript.get("path", "")
    text = manuscript_path.read_text(encoding="utf-8")
    if manuscript.get("path") != MANUSCRIPT_PATH:
        raise ValueError("unexpected manuscript path")
    if repository_sha256(manuscript_path) != manuscript.get("repository_sha256"):
        raise ValueError("manuscript SHA-256 mismatch")
    if manuscript_word_count(text) != manuscript.get("word_count"):
        raise ValueError("manuscript word count mismatch")
    if not 4_000 <= manuscript["word_count"] <= 7_000:
        raise ValueError("manuscript word count outside requested range")
    bindings = payload.get("frozen_evidence", {})
    expected = {
        "phase3c_result_sha256": EXPECTED_PHASE3C_RESULT_SHA256,
        "external_dataset_sha256": EXPECTED_DATASET_SHA256,
        "prediction_vector_sha256": EXPECTED_PREDICTION_VECTOR_SHA256,
        "phase4a_analysis_sha256": EXPECTED_ANALYSIS_SHA256,
        "model_state_sha256": EXPECTED_MODEL_STATE_SHA256,
        "rf_config_sha256": EXPECTED_RF_CONFIG_SHA256,
    }
    if bindings != expected:
        raise ValueError("manuscript frozen-evidence binding changed")
    if set(payload.get("figures", {})) != EXPECTED_FIGURE_PATHS:
        raise ValueError("manuscript figure set changed")
    if manuscript_figure_paths(text) != EXPECTED_FIGURE_PATHS:
        raise ValueError("manuscript image links differ from evidence manifest")
    for relative, digest in payload["figures"].items():
        if repository_sha256(base / relative) != digest:
            raise ValueError(f"manuscript figure hash mismatch: {relative}")
    boundary = payload.get("scientific_boundary", {})
    if boundary != {
        "phase3c_external_test_spent": True,
        "phase4a_label": "POST-HOC / EXPLORATORY",
        "new_model_training_performed": False,
        "confirmatory_result_changed": False,
        "public_release_executed": False,
    }:
        raise ValueError("manuscript scientific boundary changed")
    return payload

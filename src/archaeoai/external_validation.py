"""Frozen, pre-score infrastructure for E001 independent external validation."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable, Mapping
from enum import StrEnum
from pathlib import Path
from typing import Any

import numpy as np

from archaeoai.terrain.privacy import assert_coordinate_safe_mapping

EXPECTED_PROTOCOL_SCHEMA = "e001-phase-3a-external-validation-v1"
EXPECTED_EXPANSION_RULE_SCHEMA = "e001-phase-3b-r1-selection-rule-v1"
EXPECTED_EXPANSION_FALLBACK_SCHEMA = "e001-phase-3b-r1-multicell-fallback-rule-v1"
EXPECTED_PRIMARY_CONFIG_SHA256 = "20cd377c17373eeeb5403c84119084287f193d93b42c8004d99c823e01a157e4"
EXPECTED_MODEL_STATE_SHA256 = "e3b0c072f437e889f09a2a2cf5a37f19b2f483eb5188e102b132a89ee76d1939"
EXTERNAL_CELL_SIZE_M = 25_000
EXTERNAL_CELL_ID = "BNG_25KM_E16_N5"
MINIMUM_EXTERNAL_SEPARATION_M = 15_000.0
TARGET_POSITIVES = 60
MINIMUM_POSITIVES = 50
SELECTION_SEED = "E001-Phase-3A-external-selection-2026-08-30"
BOOTSTRAP_SEED = 20260830
BOOTSTRAP_REPLICATES = 10_000


class ExternalReviewStatus(StrEnum):
    """Private curation states allowed before the external dataset is frozen."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    UNCERTAIN = "uncertain"
    TERRAIN_REVIEW_NEEDED = "terrain_review_needed"


def protocol_hash(payload: Mapping[str, Any]) -> str:
    """Hash canonical JSON while excluding the self-referential digest field."""
    content = {key: value for key, value in payload.items() if key != "protocol_sha256"}
    encoded = json.dumps(content, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def expansion_rule_hash(payload: Mapping[str, Any]) -> str:
    """Hash a canonical expansion rule without its self-referential receipt."""
    content = {key: value for key, value in payload.items() if key != "selection_rule_sha256"}
    encoded = json.dumps(content, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def expansion_fallback_hash(payload: Mapping[str, Any]) -> str:
    """Hash a canonical fallback rule without its self-referential receipt."""
    content = {key: value for key, value in payload.items() if key != "fallback_rule_sha256"}
    encoded = json.dumps(content, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def validate_expansion_selection_rule(path: str | Path) -> dict[str, Any]:
    """Validate the pre-search Phase 3B-R1 rule without selecting a region."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    assert_coordinate_safe_mapping(payload)
    if payload.get("schema_version") != EXPECTED_EXPANSION_RULE_SCHEMA:
        raise ValueError("unexpected Phase 3B-R1 selection-rule schema")
    if payload.get("status") != "RULE_FROZEN_BEFORE_SEARCH" or payload.get("frozen") is not True:
        raise ValueError("Phase 3B-R1 selection rule is not frozen")
    if expansion_rule_hash(payload) != payload.get("selection_rule_sha256"):
        raise ValueError("Phase 3B-R1 selection-rule hash mismatch")
    sample = payload.get("frozen_sample_design", {})
    if sample.get("target_positive_count") != 60 or sample.get("minimum_positive_count") != 50:
        raise ValueError("Phase 3B-R1 changed the frozen sample design")
    geography = payload.get("candidate_cell_definition", {})
    if geography.get("first_external_cell") != EXTERNAL_CELL_ID:
        raise ValueError("Phase 3B-R1 changed the first external cell")
    if geography.get("minimum_record_separation_from_all_E001_observations_m") != 15_000:
        raise ValueError("Phase 3B-R1 weakened E001 separation")
    eligibility = payload.get("metadata_eligibility", {})
    if eligibility.get("minimum_QA_pass_probable_records") != 28:
        raise ValueError("Phase 3B-R1 metadata feasibility threshold changed")
    if eligibility.get("RF_scores_or_model_outputs_allowed") is not False:
        raise ValueError("Phase 3B-R1 must prohibit model-informed geography selection")
    selection = payload.get("deterministic_selection_rule", {})
    if selection.get("selected_cell") is not None or selection.get("performance_used") is not False:
        raise ValueError("pre-search Phase 3B-R1 rule must not contain a selected cell")
    if any(payload.get("execution_state", {}).values()):
        raise ValueError("pre-search Phase 3B-R1 execution state is contaminated")
    return payload


def validate_expansion_fallback_rule(path: str | Path) -> dict[str, Any]:
    """Validate the frozen multi-cell fallback before terrain metadata search."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    assert_coordinate_safe_mapping(payload)
    if payload.get("schema_version") != EXPECTED_EXPANSION_FALLBACK_SCHEMA:
        raise ValueError("unexpected Phase 3B-R1 fallback-rule schema")
    if payload.get("status") != "FALLBACK_FROZEN_BEFORE_TERRAIN_METADATA_SEARCH":
        raise ValueError("Phase 3B-R1 fallback rule has an unexpected status")
    if payload.get("frozen") is not True:
        raise ValueError("Phase 3B-R1 fallback rule is not frozen")
    if expansion_fallback_hash(payload) != payload.get("fallback_rule_sha256"):
        raise ValueError("Phase 3B-R1 fallback-rule hash mismatch")
    trigger = payload.get("trigger_evidence", {})
    if trigger.get("single_cell_required_QA_pass_probable_records") != 28:
        raise ValueError("Phase 3B-R1 fallback weakened the single-cell threshold")
    if trigger.get("single_cell_rule_passed") is not False:
        raise ValueError("Phase 3B-R1 fallback lacks a valid no-go trigger")
    selection = payload.get("deterministic_multicell_rule", {})
    if selection.get("combined_minimum_QA_pass_probable_records") != 28:
        raise ValueError("Phase 3B-R1 fallback changed the combined feasibility threshold")
    if selection.get("maximum_cells") != 5:
        raise ValueError("Phase 3B-R1 fallback must remain bounded to five cells")
    if selection.get("selected_cells") is not None:
        raise ValueError("pre-search fallback must not contain selected cells")
    if selection.get("performance_used") is not False:
        raise ValueError("Phase 3B-R1 fallback must prohibit model-informed selection")
    if any(payload.get("execution_state", {}).values()):
        raise ValueError("pre-search Phase 3B-R1 fallback execution state is contaminated")
    if any(payload.get("scientific_invariants", {}).values()):
        raise ValueError("Phase 3B-R1 fallback changed a scientific invariant")
    return payload


def artifact_digest_matches(
    path: str | Path, *, native_sha256: str, repository_sha256: str
) -> bool:
    """Accept the frozen native receipt or Git's canonical repository bytes.

    Earlier frozen artifacts contain mixed historical line endings. Git normalizes
    their tracked bytes on Linux, while the original receipts bind the Windows
    working-copy bytes. Both explicit digests represent the same immutable file.
    """
    observed = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return observed in {native_sha256, repository_sha256}


def validate_external_protocol(path: str | Path) -> dict[str, Any]:
    """Validate the frozen Phase 3A protocol without loading a model or terrain."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    assert_coordinate_safe_mapping(payload)
    expected = payload.get("protocol_sha256")
    if not isinstance(expected, str) or protocol_hash(payload) != expected:
        raise ValueError("Phase 3A external-validation protocol hash mismatch")
    if payload.get("schema_version") != EXPECTED_PROTOCOL_SCHEMA:
        raise ValueError("unexpected Phase 3A external-validation schema")
    if payload.get("frozen") is not True:
        raise ValueError("Phase 3A external-validation protocol is not frozen")
    if payload.get("status") != "READY_FOR_EXTERNAL_DATASET_CONSTRUCTION":
        raise ValueError("Phase 3A protocol has an unexpected status")
    if payload.get("primary_config_sha256") != EXPECTED_PRIMARY_CONFIG_SHA256:
        raise ValueError("Phase 3A protocol does not bind the frozen Random Forest config")
    if payload.get("model", {}).get("model_state_sha256") != EXPECTED_MODEL_STATE_SHA256:
        raise ValueError("Phase 3A protocol does not bind the frozen Random Forest state")
    native_artifacts = payload.get("immutable_artifact_sha256", {})
    repository_artifacts = payload.get("immutable_artifact_repository_sha256", {})
    if (
        not isinstance(native_artifacts, dict)
        or not isinstance(repository_artifacts, dict)
        or set(native_artifacts) != set(repository_artifacts)
    ):
        raise ValueError("Phase 3A immutable artifact digests are incomplete")
    if payload.get("external_geography", {}).get("public_coarse_cell") != EXTERNAL_CELL_ID:
        raise ValueError("Phase 3A protocol does not bind the selected external cell")
    if (
        payload.get("external_geography", {}).get("minimum_separation_from_prior_data_m")
        != MINIMUM_EXTERNAL_SEPARATION_M
    ):
        raise ValueError("Phase 3A protocol changed the frozen independence buffer")
    if payload.get("sample_design", {}).get("target_positive_count") != TARGET_POSITIVES:
        raise ValueError("Phase 3A target positive count changed")
    if payload.get("sample_design", {}).get("minimum_positive_count") != MINIMUM_POSITIVES:
        raise ValueError("Phase 3A minimum positive count changed")
    evaluation = payload.get("evaluation", {})
    if evaluation.get("primary_metric") != "balanced_accuracy":
        raise ValueError("Phase 3A primary metric must remain balanced accuracy")
    if evaluation.get("classification_threshold") != 0.5:
        raise ValueError("Phase 3A classification threshold must remain 0.5")
    confidence = evaluation.get("confidence_interval", {})
    if (
        confidence.get("replicates") != BOOTSTRAP_REPLICATES
        or confidence.get("seed") != BOOTSTRAP_SEED
    ):
        raise ValueError("Phase 3A confidence-interval design changed")
    execution = payload.get("execution_state", {})
    prohibited_true = (
        "external_labels_frozen",
        "external_terrain_acquired",
        "frozen_RF_loaded_for_external_data",
        "external_RF_scoring_performed",
        "external_performance_metrics_computed",
    )
    if any(execution.get(field) is not False for field in prohibited_true):
        raise ValueError("Phase 3A setup protocol must precede external scoring")
    return payload


def coarse_cell_id(point: tuple[float, float], *, cell_size_m: int = EXTERNAL_CELL_SIZE_M) -> str:
    """Return a coarse BNG cell identifier for private in-memory coordinates."""
    if cell_size_m <= 0:
        raise ValueError("cell size must be positive")
    easting, northing = point
    return (
        f"BNG_{cell_size_m // 1000}KM_"
        f"E{math.floor(easting / cell_size_m)}_N{math.floor(northing / cell_size_m)}"
    )


def distance_to_private_domain(
    point: tuple[float, float], private_domain_extent: tuple[float, float, float, float]
) -> float:
    """Return planar distance to a private left/bottom/right/top domain extent."""
    easting, northing = point
    left, bottom, right, top = private_domain_extent
    if left >= right or bottom >= top:
        raise ValueError("private domain extent is invalid")
    delta_x = max(left - easting, 0.0, easting - right)
    delta_y = max(bottom - northing, 0.0, northing - top)
    return math.hypot(delta_x, delta_y)


def assert_external_independence(
    point: tuple[float, float],
    *,
    prior_observation_centres: Iterable[tuple[float, float]],
    private_domain_extent: tuple[float, float, float, float],
    expected_cell: str = EXTERNAL_CELL_ID,
    minimum_separation_m: float = MINIMUM_EXTERNAL_SEPARATION_M,
) -> None:
    """Enforce the frozen geography gate using private coordinates only."""
    if coarse_cell_id(point) != expected_cell:
        raise ValueError("external record lies outside the frozen coarse cell")
    centres = tuple(prior_observation_centres)
    if not centres:
        raise ValueError("independence audit requires every prior observation centre")
    if minimum_separation_m <= 0:
        raise ValueError("minimum external separation must be positive")
    if min(math.dist(point, centre) for centre in centres) < minimum_separation_m:
        raise ValueError("external record violates the E001 separation buffer")
    if distance_to_private_domain(point, private_domain_extent) < minimum_separation_m:
        raise ValueError("external record violates the Phase 2F separation buffer")


def selected_positive_ids(
    accepted_ids: Iterable[str | int],
    *,
    target_count: int = TARGET_POSITIVES,
    minimum_count: int = MINIMUM_POSITIVES,
    seed: str = SELECTION_SEED,
) -> tuple[str, ...]:
    """Select at most the frozen target without consulting model output."""
    unique = {str(identifier) for identifier in accepted_ids}
    if len(unique) < minimum_count:
        raise ValueError("fewer than 50 accepted positives: external scoring is prohibited")
    if target_count < minimum_count:
        raise ValueError("target count cannot be below the minimum viable count")
    ranked = sorted(
        unique,
        key=lambda identifier: hashlib.sha256(f"{seed}:{identifier}".encode()).hexdigest(),
    )
    return tuple(ranked[:target_count])


def paired_cluster_bootstrap_indices(
    pair_count: int,
    *,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> np.ndarray:
    """Resample matched positive/background pairs for the preregistered CI."""
    if pair_count < MINIMUM_POSITIVES:
        raise ValueError("external confidence intervals require at least 50 matched pairs")
    if replicates <= 0:
        raise ValueError("bootstrap replicate count must be positive")
    generator = np.random.default_rng(seed)
    return generator.integers(0, pair_count, size=(replicates, pair_count), dtype=np.int32)


def classify_external_result(
    balanced_accuracy: float, lower_95: float, upper_95: float, *, pair_count: int
) -> str:
    """Apply the frozen interpretation rule after a future authorized evaluation."""
    if pair_count < MINIMUM_POSITIVES or not all(
        math.isfinite(value) for value in (balanced_accuracy, lower_95, upper_95)
    ):
        return "MORE_DATA_REQUIRED"
    if not 0 <= lower_95 <= balanced_accuracy <= upper_95 <= 1:
        raise ValueError("external metric and interval are inconsistent")
    if balanced_accuracy >= 0.75 and lower_95 > 0.5:
        return "EXTERNAL_GENERALIZATION_SUPPORTED"
    if balanced_accuracy > 0.5:
        return "EXTERNAL_GENERALIZATION_PARTIALLY_SUPPORTED"
    return "EXTERNAL_GENERALIZATION_NOT_SUPPORTED"


def validate_private_manifest(payload: Mapping[str, Any]) -> None:
    """Validate a private pre-score manifest without allowing result contamination."""
    if payload.get("stage") not in {"curation", "terrain_acquisition", "dataset_freeze"}:
        raise ValueError("unexpected external private-manifest stage")
    if payload.get("external_RF_scoring_performed") is not False:
        raise ValueError("external private manifest must remain pre-score")
    records = payload.get("records")
    if not isinstance(records, list):
        raise ValueError("external private manifest records must be a list")
    allowed_statuses = {status.value for status in ExternalReviewStatus}
    for record in records:
        if not isinstance(record, Mapping):
            raise ValueError("external private manifest record must be a mapping")
        if record.get("review_status") not in allowed_statuses:
            raise ValueError("external private manifest has an invalid review status")
        forbidden = {"model_score", "prediction", "predicted_label", "probability"}
        if forbidden.intersection(record):
            raise ValueError("model output is prohibited before the external dataset freeze")

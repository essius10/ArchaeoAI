import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from archaeoai.external_validation import (
    BOOTSTRAP_REPLICATES,
    BOOTSTRAP_SEED,
    EXPECTED_MODEL_STATE_SHA256,
    EXPECTED_PRIMARY_CONFIG_SHA256,
    EXTERNAL_CELL_ID,
    MINIMUM_EXTERNAL_SEPARATION_M,
    artifact_digest_matches,
    assert_external_independence,
    classify_external_result,
    coarse_cell_id,
    expansion_amendment_hash,
    expansion_fallback_hash,
    expansion_feasibility_hash,
    expansion_rule_hash,
    paired_cluster_bootstrap_indices,
    protocol_hash,
    selected_positive_ids,
    validate_expansion_amendment,
    validate_expansion_fallback_rule,
    validate_expansion_feasibility,
    validate_expansion_selection_rule,
    validate_external_protocol,
    validate_private_manifest,
)
from archaeoai.terrain.privacy import assert_coordinate_safe_mapping

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "configs/e001-phase-3a-external-validation.json"
FEASIBILITY_PATH = ROOT / "outputs/external_validation/e001_phase3a_feasibility.json"
CURATION_GATE_PATH = ROOT / "outputs/external_validation/e001_phase3b_curation_gate.json"
EXPANSION_RULE_PATH = ROOT / "configs/e001-phase-3b-r1-selection-rule.json"
EXPANSION_FALLBACK_PATH = ROOT / "configs/e001-phase-3b-r1-multicell-fallback-rule.json"
EXPANSION_FEASIBILITY_PATH = (
    ROOT / "outputs/external_validation/e001_phase3b_r1_expansion_feasibility.json"
)
EXPANSION_AMENDMENT_PATH = ROOT / "configs/e001-phase-3b-r1-expansion-amendment.json"


def test_external_protocol_is_hash_frozen_before_model_access() -> None:
    protocol = validate_external_protocol(PROTOCOL_PATH)
    assert protocol_hash(protocol) == protocol["protocol_sha256"]
    assert protocol["primary_config_sha256"] == EXPECTED_PRIMARY_CONFIG_SHA256
    assert protocol["model"]["model_state_sha256"] == EXPECTED_MODEL_STATE_SHA256
    assert protocol["execution_state"]["frozen_RF_loaded_for_external_data"] is False
    assert protocol["execution_state"]["external_RF_scoring_performed"] is False
    assert protocol["execution_state"]["external_performance_metrics_computed"] is False


def test_external_protocol_preserves_frozen_pipeline_and_metrics() -> None:
    protocol = validate_external_protocol(PROTOCOL_PATH)
    assert protocol["terrain"]["patch_dimensions_pixels"] == [128, 128]
    assert protocol["preprocessing"]["representations_in_order"] == [
        "elevation_normalized",
        "slope_degrees",
        "hillshade_315_45",
        "local_relief_r16m",
    ]
    assert protocol["preprocessing"]["pooling"]["block_shape"] == [4, 4]
    assert protocol["preprocessing"]["feature_count"] == 4096
    assert protocol["model"]["parameters"] == {
        "n_estimators": 300,
        "max_depth": 8,
        "min_samples_leaf": 5,
        "max_features": "sqrt",
        "n_jobs": 1,
        "random_state": 20260829,
    }
    assert protocol["evaluation"]["primary_metric"] == "balanced_accuracy"
    assert protocol["evaluation"]["classification_threshold"] == 0.5


def test_external_protocol_binds_immutable_prior_artifacts() -> None:
    protocol = validate_external_protocol(PROTOCOL_PATH)
    native = protocol["immutable_artifact_sha256"]
    repository = protocol["immutable_artifact_repository_sha256"]
    assert set(native) == set(repository)
    assert any(native[path] != repository[path] for path in native)
    for relative, expected in native.items():
        assert artifact_digest_matches(
            ROOT / relative,
            native_sha256=expected,
            repository_sha256=repository[relative],
        )


def test_external_feasibility_receipt_is_aggregate_and_pre_score() -> None:
    receipt = json.loads(FEASIBILITY_PATH.read_text(encoding="utf-8"))
    assert_coordinate_safe_mapping(receipt)
    assert receipt["external_geography"]["public_coarse_cell"] == EXTERNAL_CELL_ID
    assert receipt["external_geography"]["E001_positive_observations_in_cell"] == 0
    assert receipt["external_geography"]["E001_background_observations_in_cell"] == 0
    assert receipt["counts"]["eligible_after_frozen_private_separation_checks"] == 87
    assert receipt["counts"]["complete_1m_DTM_patch_coverage"] == 87
    assert receipt["counts"]["single_provenance_signature_pass"] == 86
    assert receipt["counts"]["verified_external_positive_labels"] == 0
    assert receipt["execution_state"]["external_RF_scoring_performed"] is False
    assert receipt["execution_state"]["external_performance_metrics_computed"] is False


def test_phase3b_stops_before_dataset_or_scoring_when_minimum_is_unmet() -> None:
    receipt = json.loads(CURATION_GATE_PATH.read_text(encoding="utf-8"))
    assert_coordinate_safe_mapping(receipt)
    assert receipt["status"] == "INSUFFICIENT_EXTERNAL_SAMPLE"
    assert receipt["counts"] == {
        "probable_records_reviewed": 87,
        "accepted": 47,
        "rejected": 36,
        "uncertain": 3,
        "terrain_review_needed": 1,
        "maximum_possible_after_strict_label_evidence_gate": 48,
        "minimum_required": 50,
    }
    assert receipt["decision"]["minimum_sample_gate_passed"] is False
    assert receipt["decision"]["background_construction_started"] is False
    assert receipt["decision"]["terrain_rasters_downloaded"] is False
    assert receipt["decision"]["representations_generated"] is False
    assert receipt["decision"]["external_dataset_frozen"] is False
    assert receipt["decision"]["external_dataset_sha256"] is None
    assert not any(receipt["execution_state"].values())


def test_phase3b_r1_rule_is_frozen_before_supplementary_search() -> None:
    rule = validate_expansion_selection_rule(EXPANSION_RULE_PATH)
    assert expansion_rule_hash(rule) == rule["selection_rule_sha256"]
    assert rule["frozen_sample_design"]["existing_accepted_records_locked"] == 47
    assert rule["frozen_sample_design"]["target_positive_count"] == 60
    assert rule["frozen_sample_design"]["minimum_positive_count"] == 50
    assert (
        rule["candidate_cell_definition"]["minimum_chebyshev_cell_index_difference_from_first_cell"]
        == 2
    )
    assert rule["metadata_eligibility"]["minimum_QA_pass_probable_records"] == 28
    assert rule["deterministic_selection_rule"]["selected_cell"] is None
    assert not any(rule["execution_state"].values())


def test_phase3b_r1_multicell_fallback_is_frozen_before_terrain_metadata_search() -> None:
    fallback = validate_expansion_fallback_rule(EXPANSION_FALLBACK_PATH)
    assert expansion_fallback_hash(fallback) == fallback["fallback_rule_sha256"]
    assert fallback["source_selection_rule_sha256"] == (
        "6e5f2992fe453601940792ad4c1f7be373c12724f5849f43926c7ea680459578"
    )
    assert fallback["trigger_evidence"]["largest_single_cell_independent_probable_records"] == 11
    assert (
        fallback["deterministic_multicell_rule"]["combined_minimum_QA_pass_probable_records"] == 28
    )
    assert fallback["deterministic_multicell_rule"]["maximum_cells"] == 5
    assert fallback["deterministic_multicell_rule"]["selected_cells"] is None
    assert not any(fallback["execution_state"].values())


def test_phase3b_r1_feasibility_selects_only_the_frozen_metadata_ranked_prefix() -> None:
    receipt = validate_expansion_feasibility(EXPANSION_FEASIBILITY_PATH)
    assert expansion_feasibility_hash(receipt) == receipt["feasibility_receipt_sha256"]
    assert receipt["candidate_search"] == {
        "independent_candidate_cells_identified": 40,
        "cells_meeting_preterrain_minimum": 9,
        "single_cell_threshold": 28,
        "largest_single_cell_independent_probable_records": 11,
        "single_cell_rule_passed": False,
    }
    assert receipt["selection"]["aggregate_independent_probable_records"] == 33
    assert receipt["selection"]["aggregate_QA_pass_probable_records"] == 31
    assert receipt["selection"]["performance_used"] is False
    assert not any(receipt["execution_state"].values())


def test_phase3b_r1_amendment_freezes_multi_region_design_before_scoring() -> None:
    amendment = validate_expansion_amendment(EXPANSION_AMENDMENT_PATH)
    assert expansion_amendment_hash(amendment) == amendment["amendment_sha256"]
    assert amendment["first_region_decisions"] == {
        "accepted_locked": 47,
        "rejected_locked": 36,
        "uncertain_locked": 3,
        "terrain_review_needed": 1,
        "reclassification_for_sample_size_prohibited": True,
    }
    assert amendment["sample_design"]["target_positive_count"] == 60
    assert amendment["sample_design"]["minimum_positive_count"] == 50
    assert amendment["analysis_policy"]["primary_metric"] == "balanced_accuracy"
    assert amendment["analysis_policy"]["regional_results_are_secondary_descriptive_only"]
    assert not any(amendment["execution_state"].values())


def test_phase3b_r1_selection_script_cannot_overwrite_frozen_receipt() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/select_e001_external_expansion.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "refusing to overwrite" in result.stderr


def test_external_spatial_gate_accepts_only_independent_synthetic_point() -> None:
    point = (412_500.0, 137_500.0)
    prior = ((450_000.0, 137_500.0), (380_000.0, 100_000.0))
    private_domain = (460_000.0, 100_000.0, 465_000.0, 105_000.0)
    assert coarse_cell_id(point) == EXTERNAL_CELL_ID
    assert_external_independence(
        point,
        prior_observation_centres=prior,
        private_domain_extent=private_domain,
    )


@pytest.mark.parametrize(
    ("point", "prior", "private_domain", "message"),
    [
        (
            (430_000.0, 137_500.0),
            ((460_000.0, 137_500.0),),
            (470_000.0, 100_000.0, 475_000.0, 105_000.0),
            "outside the frozen coarse cell",
        ),
        (
            (412_500.0, 137_500.0),
            ((412_600.0, 137_500.0),),
            (470_000.0, 100_000.0, 475_000.0, 105_000.0),
            "E001 separation",
        ),
        (
            (412_500.0, 137_500.0),
            ((450_000.0, 137_500.0),),
            (410_000.0, 135_000.0, 415_000.0, 140_000.0),
            "Phase 2F separation",
        ),
    ],
)
def test_external_spatial_gate_rejects_contamination(
    point: tuple[float, float],
    prior: tuple[tuple[float, float], ...],
    private_domain: tuple[float, float, float, float],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        assert_external_independence(
            point,
            prior_observation_centres=prior,
            private_domain_extent=private_domain,
        )


def test_external_selection_is_deterministic_and_availability_bounded() -> None:
    accepted = [f"record-{index:03d}" for index in range(75)]
    first = selected_positive_ids(accepted)
    second = selected_positive_ids(reversed(accepted))
    assert first == second
    assert len(first) == 60
    assert len(selected_positive_ids(accepted[:55])) == 55
    with pytest.raises(ValueError, match="fewer than 50"):
        selected_positive_ids(accepted[:49])


def test_paired_cluster_bootstrap_is_deterministic_and_keeps_pairs() -> None:
    first = paired_cluster_bootstrap_indices(50)
    second = paired_cluster_bootstrap_indices(50)
    assert np.array_equal(first, second)
    assert first.shape == (BOOTSTRAP_REPLICATES, 50)
    assert first.dtype == np.int32
    assert first.min() >= 0 and first.max() < 50
    assert BOOTSTRAP_SEED == 20260830


def test_external_outcome_rule_is_frozen_before_scoring() -> None:
    assert classify_external_result(0.80, 0.65, 0.90, pair_count=60) == (
        "EXTERNAL_GENERALIZATION_SUPPORTED"
    )
    assert classify_external_result(0.70, 0.55, 0.82, pair_count=60) == (
        "EXTERNAL_GENERALIZATION_PARTIALLY_SUPPORTED"
    )
    assert classify_external_result(0.50, 0.38, 0.62, pair_count=60) == (
        "EXTERNAL_GENERALIZATION_NOT_SUPPORTED"
    )
    assert classify_external_result(0.80, 0.60, 0.90, pair_count=49) == "MORE_DATA_REQUIRED"


def test_private_manifest_guard_rejects_any_model_output() -> None:
    payload = {
        "stage": "curation",
        "external_RF_scoring_performed": False,
        "records": [{"review_status": "accepted", "easting": 1.0, "northing": 2.0}],
    }
    validate_private_manifest(payload)
    payload["records"][0]["model_score"] = 0.8
    with pytest.raises(ValueError, match="model output is prohibited"):
        validate_private_manifest(payload)


def test_external_private_path_is_ignored() -> None:
    sentinel = "data/private/e001/external_validation/private-sentinel.json"
    result = __import__("subprocess").run(
        ["git", "check-ignore", "--quiet", sentinel], cwd=ROOT, check=False
    )
    assert result.returncode == 0
    assert MINIMUM_EXTERNAL_SEPARATION_M == 15_000.0

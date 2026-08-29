import hashlib
import json
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
    assert_external_independence,
    classify_external_result,
    coarse_cell_id,
    paired_cluster_bootstrap_indices,
    protocol_hash,
    selected_positive_ids,
    validate_external_protocol,
    validate_private_manifest,
)
from archaeoai.terrain.privacy import assert_coordinate_safe_mapping

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "configs/e001-phase-3a-external-validation.json"
FEASIBILITY_PATH = ROOT / "outputs/external_validation/e001_phase3a_feasibility.json"


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
    for relative, expected in protocol["immutable_artifact_sha256"].items():
        observed = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        assert observed == expected


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

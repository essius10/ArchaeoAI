import json
from pathlib import Path

import numpy as np
import pytest
from sklearn.ensemble import RandomForestClassifier

from archaeoai.inference import (
    DEDUPLICATION_DISTANCE_M,
    EXPECTED_PRIMARY_CONFIG_SHA256,
    FEATURE_COUNT,
    PATCH_SIZE_PIXELS,
    STRIDE_PIXELS,
    PixelWindow,
    PrivateScoredWindow,
    QueueSelection,
    deduplicate_ranked,
    features_from_elevation,
    features_from_representations,
    generate_patch_grid,
    model_state_sha256,
    protocol_hash,
    rank_windows,
    safe_public_summary,
    score_feature_matrix,
    select_review_queues,
    validate_inference_protocol,
)
from archaeoai.model_data import configuration_hash, mean_pool_4x4
from archaeoai.terrain.privacy import assert_coordinate_safe_mapping, ensure_private_output
from archaeoai.terrain.representations import terrain_representations

ROOT = Path(__file__).resolve().parents[1]


def _window(token: str, row: int, column: int, score: float) -> PrivateScoredWindow:
    return PrivateScoredWindow(PixelWindow(token, row, column), score)


def test_protocol_is_frozen_before_any_real_candidate_scan() -> None:
    protocol = validate_inference_protocol(ROOT / "configs/e001-phase-2f-a-inference-protocol.json")
    assert protocol["primary_config_sha256"] == EXPECTED_PRIMARY_CONFIG_SHA256
    assert protocol["status"] == "READY_NO_REAL_SCAN"
    assert protocol["execution_state"]["new_terrain_scored"] is False
    assert protocol["execution_state"]["candidate_scores_computed"] is False
    assert protocol["execution_state"]["candidate_locations_exposed"] is False
    assert protocol_hash(protocol) == protocol["protocol_sha256"]


def test_protocol_preserves_frozen_random_forest_without_retuning() -> None:
    protocol = validate_inference_protocol(ROOT / "configs/e001-phase-2f-a-inference-protocol.json")
    assert protocol["model"]["parameters"] == {
        "n_estimators": 300,
        "max_depth": 8,
        "min_samples_leaf": 5,
        "max_features": "sqrt",
        "n_jobs": 1,
        "random_state": 20260829,
    }
    assert protocol["model"]["candidate_result_retraining_allowed"] is False
    config = json.loads(
        (ROOT / "outputs/modelling/e001_primary_baseline_config.json").read_text(encoding="utf-8")
    )
    assert configuration_hash(config) == EXPECTED_PRIMARY_CONFIG_SHA256


def test_patch_grid_is_deterministic_and_has_frozen_5km_count() -> None:
    first = generate_patch_grid((5000, 5000), private_domain_salt="synthetic-domain-salt")
    second = generate_patch_grid((5000, 5000), private_domain_salt="synthetic-domain-salt")
    assert first == second
    assert len(first) == 5929
    assert (first[0].row_offset, first[0].column_offset) == (0, 0)
    assert (first[-1].row_offset, first[-1].column_offset) == (4864, 4864)
    assert first[0].size_pixels == PATCH_SIZE_PIXELS
    assert STRIDE_PIXELS == 64


def test_patch_grid_rejects_changed_scientific_geometry() -> None:
    with pytest.raises(ValueError, match="frozen"):
        generate_patch_grid(
            (5000, 5000),
            private_domain_salt="synthetic-domain-salt",
            stride_pixels=32,
        )


def test_inference_features_match_training_feature_assembly() -> None:
    y, x = np.mgrid[-64:64, -64:64]
    elevation = (0.8 * np.exp(-((x**2 + y**2) / 300.0)) + x * 0.002).astype(np.float32)
    mask = np.zeros_like(elevation, dtype=bool)
    representations = terrain_representations(
        elevation,
        resolution_m=1.0,
        mask=mask,
        local_relief_radius_m=16.0,
        hillshade_azimuth_deg=315.0,
        hillshade_altitude_deg=45.0,
    )
    inference = features_from_elevation(elevation, mask)
    training = features_from_representations(representations)
    explicit = np.concatenate(
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
    assert inference.shape == (FEATURE_COUNT,)
    assert np.array_equal(inference, training)
    assert np.array_equal(inference, explicit)


def test_inference_features_reject_metadata_or_extra_channels() -> None:
    layers = {
        name: np.ones((128, 128), dtype=np.float32)
        for name in (
            "elevation_normalized",
            "slope_degrees",
            "hillshade_315_45",
            "local_relief_r16m",
        )
    }
    layers["survey_year"] = np.ones((128, 128), dtype=np.float32)
    with pytest.raises(ValueError, match="exactly the four"):
        features_from_representations(layers)


def test_score_and_model_state_are_deterministic() -> None:
    rng = np.random.default_rng(7)
    features = rng.normal(size=(12, FEATURE_COUNT)).astype(np.float32)
    labels = np.asarray([0, 1] * 6, dtype=np.int8)
    parameters = {
        "n_estimators": 300,
        "max_depth": 8,
        "min_samples_leaf": 5,
        "max_features": "sqrt",
        "n_jobs": 1,
        "random_state": 20260829,
    }
    first = RandomForestClassifier(**parameters).fit(features, labels)
    second = RandomForestClassifier(**parameters).fit(features, labels)
    assert model_state_sha256(first) == model_state_sha256(second)
    assert np.array_equal(
        score_feature_matrix(first, features), score_feature_matrix(second, features)
    )


def test_ranking_and_deduplication_are_deterministic() -> None:
    candidates = (
        _window("b", 0, 0, 0.8),
        _window("a", 0, 64, 0.8),
        _window("c", 256, 256, 0.7),
    )
    ranked = rank_windows(candidates)
    assert [item.window.private_token for item in ranked] == ["a", "b", "c"]
    deduplicated = deduplicate_ranked(candidates)
    assert [item.window.private_token for item in deduplicated] == ["a", "c"]
    assert DEDUPLICATION_DISTANCE_M == 128.0


def test_review_queues_are_deterministic_and_disjoint() -> None:
    candidates = tuple(
        _window(f"token-{index:03d}", index * 256, 0, index / 99) for index in range(100)
    )
    first = select_review_queues(candidates)
    second = select_review_queues(tuple(reversed(candidates)))
    assert first == second
    tokens = [
        {item.window.private_token for item in queue}
        for queue in (first.high, first.medium, first.reference)
    ]
    assert not tokens[0] & tokens[1]
    assert not tokens[0] & tokens[2]
    assert not tokens[1] & tokens[2]
    assert len(first.high) == 1
    assert len(first.medium) == 10
    assert len(first.reference) == 25


def test_public_summary_is_coordinate_safe_and_aggregate_only() -> None:
    empty = QueueSelection((), (), ())
    summary = safe_public_summary(
        total_windows=4,
        valid_scores=np.asarray([0.1, 0.2, 0.3]),
        rejected_windows=1,
        no_data_windows=0,
        representative_count=2,
        queues=empty,
        model_state_checksum="a" * 64,
    )
    assert_coordinate_safe_mapping(summary)
    serialized = json.dumps(summary).casefold()
    assert "private_token" not in serialized
    assert "sample_id" not in serialized
    assert "filename" not in serialized
    assert summary["semantics"] == ("terrain_similarity_model_score_not_archaeological_probability")


def test_candidate_artifacts_are_constrained_to_private_ignored_tree() -> None:
    allowed = ensure_private_output(
        ROOT, ROOT / "data/private/e001/inference/private-candidate-receipt.json"
    )
    assert allowed.is_relative_to(ROOT / "data/private")
    with pytest.raises(ValueError, match="must remain"):
        ensure_private_output(ROOT, ROOT / "outputs/inference/candidates.json")

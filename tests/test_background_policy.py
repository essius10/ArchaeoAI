import pytest

from archaeoai.terrain.acquisition import terrain_provenance_id
from archaeoai.terrain.background import (
    BACKGROUND_LABEL,
    BackgroundIndexRecord,
    BackgroundSamplingPolicy,
    candidate_rejection_reason,
    generate_candidate,
    geographic_group_id,
    opaque_background_id,
    validate_background_index,
    violates_minimum_distance,
)


def test_background_policy_uses_uncertainty_aware_label() -> None:
    policy = BackgroundSamplingPolicy()

    assert policy.label == "unlabelled_background"
    assert policy.require_survey_provenance_matching
    assert policy.require_geographic_group_assignment


def test_true_negative_label_is_rejected() -> None:
    with pytest.raises(ValueError, match="unlabelled_background"):
        BackgroundSamplingPolicy(label="true_negative")


def test_primary_policy_freezes_balanced_ratio_and_distances() -> None:
    policy = BackgroundSamplingPolicy()

    assert policy.backgrounds_per_positive == 1
    assert policy.positive_exclusion_buffer_m == 500
    assert policy.known_archaeology_exclusion_buffer_m == 250
    assert policy.minimum_sample_separation_m == 256


def test_background_ids_and_candidates_are_deterministic() -> None:
    policy = BackgroundSamplingPolicy()
    first = generate_candidate(
        "E001P-test", positive_centre=(350000, 250000), attempt=1, policy=policy
    )
    second = generate_candidate(
        "E001P-test", positive_centre=(350000, 250000), attempt=1, policy=policy
    )

    assert first == second
    assert opaque_background_id("E001P-test", 1) == opaque_background_id("E001P-test", 1)
    assert opaque_background_id("E001P-test", 1) != opaque_background_id("E001P-test", 2)


def test_candidate_lies_inside_area_uniform_annulus() -> None:
    policy = BackgroundSamplingPolicy()
    candidate = generate_candidate(
        "E001P-test", positive_centre=(350000, 250000), attempt=7, policy=policy
    )
    distance = ((candidate.easting - 350000) ** 2 + (candidate.northing - 250000) ** 2) ** 0.5

    assert policy.sampling_radius_min_m <= distance <= policy.sampling_radius_max_m
    assert geographic_group_id((350000, 250000)) == "BNG_100KM_E3_N2"


def test_positive_and_background_spacing_are_strict() -> None:
    assert violates_minimum_distance((0, 0), ((300, 400),), minimum_m=501)
    assert not violates_minimum_distance((0, 0), ((300, 400),), minimum_m=500)


@pytest.mark.parametrize(
    ("candidate", "positive_centres", "background_centres", "known", "expected"),
    [
        ((299999, 250000), (), (), False, "outside_geographic_group"),
        ((350000, 250000), ((350300, 250000),), (), False, "positive_exclusion"),
        ((350000, 250000), (), ((350100, 250000),), False, "too_close_background"),
        ((350000, 250000), (), (), True, "known_archaeology_exclusion"),
        ((350000, 250000), (), (), False, None),
    ],
)
def test_candidate_rejection_policy(
    candidate: tuple[float, float],
    positive_centres: tuple[tuple[float, float], ...],
    background_centres: tuple[tuple[float, float], ...],
    known: bool,
    expected: str | None,
) -> None:
    assert (
        candidate_rejection_reason(
            candidate,
            expected_geographic_group_id="BNG_100KM_E3_N2",
            positive_centres=positive_centres,
            background_centres=background_centres,
            known_scheduled_monument_present=known,
            policy=BackgroundSamplingPolicy(),
        )
        == expected
    )


def test_forbidden_negative_terminology_is_absent_from_public_label() -> None:
    assert BACKGROUND_LABEL == "unlabelled_background"


def test_terrain_provenance_identity_requires_exact_metadata_match() -> None:
    expected = terrain_provenance_id("2021", "1", "National Programme")

    assert expected == terrain_provenance_id("2021", "1", "National Programme")
    assert expected != terrain_provenance_id("2020", "1", "National Programme")
    assert expected != terrain_provenance_id("2021", "0.5", "National Programme")
    assert expected != terrain_provenance_id("2021", "1", "Local Programme")


def _valid_index_record(**overrides: object) -> BackgroundIndexRecord:
    values: dict[str, object] = {
        "sample_id": "E001B-000000000001",
        "class_label": BACKGROUND_LABEL,
        "observation_group_id": "E001G-000000000001",
        "geographic_group_id": "BNG_100KM_E3_N2",
        "terrain_provenance_id": "EAP-000000000001",
        "survey_year": "2021",
        "source_resolution_m": 1.0,
        "patch_size_m": 128,
        "sampling_algorithm_version": "e001-background-v1",
        "processing_version": "e001-terrain-v1",
        "sampling_stratum": "E001S-000000000001",
        "acquisition_status": "verified",
        "raw_qa_status": "pass",
        "representation_qa_status": "pass",
        "qa_status": "pass",
        "raw_sha256": "a" * 64,
        "patch_sha256": "b" * 64,
        "processed_sha256": "c" * 64,
        "cross_cell": False,
    }
    values.update(overrides)
    return BackgroundIndexRecord(**values)  # type: ignore[arg-type]


def test_safe_background_index_accepts_only_fully_verified_rows() -> None:
    validate_background_index([_valid_index_record()])

    with pytest.raises(ValueError, match="QA-passed"):
        validate_background_index([_valid_index_record(qa_status="failed")])


def test_background_index_rejects_bad_checksum_and_duplicate_terrain() -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        validate_background_index([_valid_index_record(raw_sha256="not-a-digest")])

    with pytest.raises(ValueError, match="duplicate exact background terrain"):
        validate_background_index(
            [
                _valid_index_record(),
                _valid_index_record(
                    sample_id="E001B-000000000002",
                    raw_sha256="d" * 64,
                    processed_sha256="e" * 64,
                ),
            ]
        )

import json
from pathlib import Path

import pytest

from archaeoai.inference_system import (
    E001_TERRAIN_INPUT,
    AutomaticInferenceResult,
    EvidenceLevel,
    LimitationCode,
    ModelArtifactIntegrityError,
    ModelArtifactUnavailableError,
    ModelIdentifier,
    TerrainInputMetadata,
    WarningCode,
    verify_model_artifact_checksum,
)
from archaeoai.inference_system.contracts import (
    APPROVED_MODEL_CONFIG_SHA256,
    LIMITATION_MESSAGES,
    PUBLIC_RESULT_FIELDS,
    SCORE_SEMANTICS,
    WARNING_MESSAGES,
    TerrainInputValidationError,
)

FROZEN_CONFIG_SHA256 = "20cd377c17373eeeb5403c84119084287f193d93b42c8004d99c823e01a157e4"


class _UnexpectedObject:
    pass


def _valid_metadata(**overrides: object) -> TerrainInputMetadata:
    values: dict[str, object] = {
        "crs": "EPSG:27700",
        "width": 128,
        "height": 128,
        "resolution_m": (1.0, 1.0),
        "band_count": 1,
        "nodata_fraction": 0.2,
    }
    values.update(overrides)
    return TerrainInputMetadata(**values)  # type: ignore[arg-type]


def _automatic_result(**overrides: object) -> AutomaticInferenceResult:
    values: dict[str, object] = {
        "terrain_similarity_score": 0.75,
        "evidence_level": EvidenceLevel.AI_OUTPUT,
        "model_identifier": ModelIdentifier.E001_FROZEN_RANDOM_FOREST,
        "model_config_sha256": FROZEN_CONFIG_SHA256,
    }
    values.update(overrides)
    return AutomaticInferenceResult(**values)  # type: ignore[arg-type]


def test_evidence_ladder_is_explicit_and_complete() -> None:
    assert [level.value for level in EvidenceLevel] == [
        "AI_OUTPUT",
        "AI_HYPOTHESIS",
        "HUMAN_VETTED_OBSERVATION",
        "ARCHAEOLOGIST_VALIDATED_INTERPRETATION",
        "CONFIRMED_ARCHAEOLOGICAL_EVIDENCE",
    ]


@pytest.mark.parametrize(
    "level",
    [
        EvidenceLevel.HUMAN_VETTED_OBSERVATION,
        EvidenceLevel.ARCHAEOLOGIST_VALIDATED_INTERPRETATION,
        EvidenceLevel.CONFIRMED_ARCHAEOLOGICAL_EVIDENCE,
    ],
)
def test_automatic_inference_cannot_emit_reviewed_or_confirmed_evidence(
    level: EvidenceLevel,
) -> None:
    with pytest.raises(ValueError, match="cannot assert human or archaeological review"):
        _automatic_result(evidence_level=level)


def test_public_result_uses_terrain_similarity_not_site_probability() -> None:
    payload = _automatic_result().to_public_dict()
    assert payload["score_semantics"] == SCORE_SEMANTICS
    assert "terrain_similarity_score" in payload
    assert all("probability" not in key for key in payload)
    assert "site" not in payload["score_semantics"]


def test_public_result_is_explicit_deterministic_json_safe_allowlist() -> None:
    result = _automatic_result()
    first = result.to_public_dict()
    second = result.to_public_dict()
    first_json = json.dumps(first, sort_keys=True, allow_nan=False)
    second_json = json.dumps(second, sort_keys=True, allow_nan=False)

    assert first == second
    assert first_json == second_json
    assert json.loads(first_json) == first
    assert set(first) == PUBLIC_RESULT_FIELDS
    assert first["warnings"] == [
        WARNING_MESSAGES[WarningCode.HUMAN_REVIEW_REQUIRED],
        WARNING_MESSAGES[WarningCode.AUTOMATIC_EVIDENCE_ONLY],
    ]
    assert first["limitations"] == [
        LIMITATION_MESSAGES[LimitationCode.NOT_ARCHAEOLOGICAL_PROBABILITY],
        LIMITATION_MESSAGES[LimitationCode.NOT_ARCHAEOLOGICAL_CONFIRMATION],
        LIMITATION_MESSAGES[LimitationCode.E001_SCOPE_ONLY],
    ]


def test_every_controlled_message_code_has_fixed_public_rendering() -> None:
    assert set(WARNING_MESSAGES) == set(WarningCode)
    assert set(LIMITATION_MESSAGES) == set(LimitationCode)
    assert set(APPROVED_MODEL_CONFIG_SHA256) == set(ModelIdentifier)


def test_private_metadata_is_excluded_from_public_serialization() -> None:
    payload = _automatic_result(
        private_metadata={
            "easting": "fictional-private-value",
            "northing": "fictional-private-value",
            "source_path": "private-input.tif",
        }
    ).to_public_dict()
    serialized = json.dumps(payload).casefold()
    for forbidden in ("easting", "northing", "source_path", "private-input"):
        assert forbidden not in serialized


@pytest.mark.parametrize("field_name", ["warnings", "limitations"])
@pytest.mark.parametrize(
    "unsafe_value",
    [
        (r"C:\Users\fictional\private-terrain.tif",),
        ("/home/fictional/private-terrain.tif",),
        ({"nested": {"source_path": "/private/input.tif"}},),
        [{"source_path": "/private/input.tif"}],
        ([{"easting": 123456}],),
        (_UnexpectedObject(),),
        ("CONFIRMED ARCHAEOLOGICAL DISCOVERY",),
        ("ARCHAEOLOGIST VALIDATED SITE",),
        ("ARCHAEOLOGICAL SITE PROBABILITY 99 PERCENT",),
        ("DISCOVERY CONFIRMED",),
    ],
)
def test_free_form_public_messages_fail_closed(field_name: str, unsafe_value: object) -> None:
    with pytest.raises(TypeError, match="tuple of approved"):
        _automatic_result(**{field_name: unsafe_value})


@pytest.mark.parametrize("field_name", ["warnings", "limitations"])
def test_required_safety_codes_cannot_be_omitted(field_name: str) -> None:
    with pytest.raises(ValueError, match="missing required safety codes"):
        _automatic_result(**{field_name: ()})


def test_warning_and_limitation_code_types_cannot_be_crossed() -> None:
    with pytest.raises(TypeError, match="approved WarningCode"):
        _automatic_result(
            warnings=(
                WarningCode.HUMAN_REVIEW_REQUIRED,
                LimitationCode.NOT_ARCHAEOLOGICAL_CONFIRMATION,
            )
        )
    with pytest.raises(TypeError, match="approved LimitationCode"):
        _automatic_result(
            limitations=(
                LimitationCode.NOT_ARCHAEOLOGICAL_PROBABILITY,
                LimitationCode.NOT_ARCHAEOLOGICAL_CONFIRMATION,
                WarningCode.AUTOMATIC_EVIDENCE_ONLY,
            )
        )


@pytest.mark.parametrize(
    "identifier",
    [
        "/private/model",
        r"C:\private\model.pkl",
        r"\\server\share\model.pkl",
        "../model",
        "file:///private/model",
        "https://example.invalid/model",
        " e001-rf-v1",
        "e001 rf v1",
        "e001\nrf",
        "e001\trf",
        "e001--rf",
        "E001-RF-V1",
        "a" * 65,
        "",
    ],
)
def test_unsafe_model_identifiers_fail_closed(identifier: str) -> None:
    with pytest.raises(ValueError, match="lowercase alphanumeric hyphen slug"):
        _automatic_result(model_identifier=identifier)


@pytest.mark.parametrize("identifier", list(ModelIdentifier))
def test_safe_model_identifiers_are_accepted(identifier: ModelIdentifier) -> None:
    assert _automatic_result(model_identifier=identifier).to_public_dict()["model_identifier"] == (
        identifier.value
    )


@pytest.mark.parametrize("identifier", ["e001", "e001-rf-v1", "model2026", "rf-300-tree"])
def test_unapproved_model_identifier_slugs_fail_closed(identifier: str) -> None:
    with pytest.raises(TypeError, match="approved ModelIdentifier"):
        _automatic_result(model_identifier=identifier)


def test_model_identifier_is_bound_to_approved_configuration() -> None:
    with pytest.raises(ValueError, match="does not match the approved model identifier"):
        _automatic_result(model_config_sha256="a" * 64)


@pytest.mark.parametrize(
    ("overrides", "error", "message"),
    [
        ({"terrain_similarity_score": 1}, ValueError, "finite float"),
        ({"evidence_level": "AI_OUTPUT"}, TypeError, "EvidenceLevel"),
        ({"model_identifier": 123}, ValueError, "lowercase alphanumeric"),
        ({"model_config_sha256": b"a" * 64}, ValueError, "lowercase SHA-256"),
        ({"private_metadata": []}, TypeError, "must be a mapping"),
    ],
)
def test_public_result_runtime_types_fail_closed(
    overrides: dict[str, object], error: type[Exception], message: str
) -> None:
    with pytest.raises(error, match=message):
        _automatic_result(**overrides)


def test_valid_e001_patch_metadata_passes_without_reprojection() -> None:
    E001_TERRAIN_INPUT.validate(_valid_metadata())


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"crs": "EPSG:4326"}, "crs_mismatch_no_automatic_reprojection"),
        ({"width": 256}, "dimensions_mismatch"),
        ({"resolution_m": (2.0, 2.0)}, "resolution_mismatch"),
        ({"band_count": 3}, "band_count_mismatch"),
        ({"nodata_fraction": 0.21}, "nodata_policy_failed"),
    ],
)
def test_invalid_input_metadata_fails_closed(overrides: dict[str, object], reason: str) -> None:
    with pytest.raises(TerrainInputValidationError, match=reason):
        E001_TERRAIN_INPUT.validate(_valid_metadata(**overrides))


def test_missing_model_is_explicit_and_never_triggers_retraining(tmp_path: Path) -> None:
    with pytest.raises(ModelArtifactUnavailableError, match="automatic retraining is prohibited"):
        verify_model_artifact_checksum(
            tmp_path / "absent-private-model.pkl",
            expected_sha256="a" * 64,
        )
    assert list(tmp_path.iterdir()) == []


def test_model_checksum_guard_does_not_deserialize_or_execute(tmp_path: Path) -> None:
    artifact = tmp_path / "opaque-model.bin"
    artifact.write_bytes(b"opaque synthetic test artifact")
    with pytest.raises(ModelArtifactIntegrityError, match="SHA-256 mismatch"):
        verify_model_artifact_checksum(artifact, expected_sha256="b" * 64)

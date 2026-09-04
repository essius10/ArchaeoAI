import json
from pathlib import Path

import pytest

from archaeoai.inference_system import (
    E001_TERRAIN_INPUT,
    AutomaticInferenceResult,
    EvidenceLevel,
    ModelArtifactIntegrityError,
    ModelArtifactUnavailableError,
    TerrainInputMetadata,
    verify_model_artifact_checksum,
)
from archaeoai.inference_system.contracts import SCORE_SEMANTICS, TerrainInputValidationError

FROZEN_CONFIG_SHA256 = "20cd377c17373eeeb5403c84119084287f193d93b42c8004d99c823e01a157e4"


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
        "model_identifier": "e001-frozen-random-forest",
        "model_config_sha256": FROZEN_CONFIG_SHA256,
        "warnings": ("Human review has not occurred.",),
        "limitations": ("No archaeological discovery is claimed.",),
    }
    values.update(overrides)
    return AutomaticInferenceResult(**values)  # type: ignore[arg-type]


def test_evidence_ladder_is_explicit_and_complete() -> None:
    assert [level.value for level in EvidenceLevel] == [
        "AI_OUTPUT",
        "AI_HYPOTHESIS",
        "HUMAN_REVIEWED_TERRAIN_FEATURE",
        "ARCHAEOLOGIST_REVIEWED_FEATURE",
        "CONFIRMED_ARCHAEOLOGICAL_SITE",
    ]


@pytest.mark.parametrize(
    "level",
    [
        EvidenceLevel.HUMAN_REVIEWED_TERRAIN_FEATURE,
        EvidenceLevel.ARCHAEOLOGIST_REVIEWED_FEATURE,
        EvidenceLevel.CONFIRMED_ARCHAEOLOGICAL_SITE,
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

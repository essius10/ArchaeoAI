"""Safety and serialization contracts for a future terrain-inference boundary.

Nothing in this module fits, loads, or executes a model. It provides fail-closed
validation that later Phase 5 implementation work must use.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Any

from pyproj import CRS

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
MODEL_IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAXIMUM_MODEL_IDENTIFIER_LENGTH = 64
SCORE_SEMANTICS = "terrain_pattern_similarity_not_archaeological_probability"
E001_FROZEN_CONFIG_SHA256 = "20cd377c17373eeeb5403c84119084287f193d93b42c8004d99c823e01a157e4"


class EvidenceLevel(StrEnum):
    """Evidence ladder; automatic inference is restricted to its first two levels."""

    AI_OUTPUT = "AI_OUTPUT"
    AI_HYPOTHESIS = "AI_HYPOTHESIS"
    HUMAN_VETTED_OBSERVATION = "HUMAN_VETTED_OBSERVATION"
    ARCHAEOLOGIST_VALIDATED_INTERPRETATION = "ARCHAEOLOGIST_VALIDATED_INTERPRETATION"
    CONFIRMED_ARCHAEOLOGICAL_EVIDENCE = "CONFIRMED_ARCHAEOLOGICAL_EVIDENCE"


AUTOMATIC_EVIDENCE_LEVELS = frozenset(
    {
        EvidenceLevel.AI_OUTPUT,
        EvidenceLevel.AI_HYPOTHESIS,
    }
)


class WarningCode(StrEnum):
    """Approved coordinate-safe warnings for automatic public results."""

    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    AUTOMATIC_EVIDENCE_ONLY = "AUTOMATIC_EVIDENCE_ONLY"


class LimitationCode(StrEnum):
    """Approved coordinate-safe limitations for automatic public results."""

    NOT_ARCHAEOLOGICAL_PROBABILITY = "NOT_ARCHAEOLOGICAL_PROBABILITY"
    NOT_ARCHAEOLOGICAL_CONFIRMATION = "NOT_ARCHAEOLOGICAL_CONFIRMATION"
    E001_SCOPE_ONLY = "E001_SCOPE_ONLY"


class ModelIdentifier(StrEnum):
    """Approved public identifiers; values must remain path- and metadata-free."""

    E001_FROZEN_RANDOM_FOREST = "e001-frozen-random-forest"


WARNING_MESSAGES: Mapping[WarningCode, str] = MappingProxyType(
    {
        WarningCode.HUMAN_REVIEW_REQUIRED: "Independent human review is required.",
        WarningCode.AUTOMATIC_EVIDENCE_ONLY: "This is automatic terrain-model output only.",
    }
)
LIMITATION_MESSAGES: Mapping[LimitationCode, str] = MappingProxyType(
    {
        LimitationCode.NOT_ARCHAEOLOGICAL_PROBABILITY: (
            "The score is not a probability that archaeology exists."
        ),
        LimitationCode.NOT_ARCHAEOLOGICAL_CONFIRMATION: (
            "The result does not confirm an archaeological site or discovery."
        ),
        LimitationCode.E001_SCOPE_ONLY: (
            "The model is limited to the documented E001 research scope."
        ),
    }
)
APPROVED_MODEL_CONFIG_SHA256: Mapping[ModelIdentifier, str] = MappingProxyType(
    {ModelIdentifier.E001_FROZEN_RANDOM_FOREST: E001_FROZEN_CONFIG_SHA256}
)
REQUIRED_WARNING_CODES = frozenset(
    {
        WarningCode.HUMAN_REVIEW_REQUIRED,
        WarningCode.AUTOMATIC_EVIDENCE_ONLY,
    }
)
REQUIRED_LIMITATION_CODES = frozenset(
    {
        LimitationCode.NOT_ARCHAEOLOGICAL_PROBABILITY,
        LimitationCode.NOT_ARCHAEOLOGICAL_CONFIRMATION,
        LimitationCode.E001_SCOPE_ONLY,
    }
)
PUBLIC_RESULT_FIELDS = frozenset(
    {
        "schema_version",
        "evidence_level",
        "terrain_similarity_score",
        "score_semantics",
        "model_identifier",
        "model_config_sha256",
        "warnings",
        "limitations",
    }
)


class TerrainInputValidationError(ValueError):
    """Raised when input metadata violates the frozen terrain contract."""


class ModelArtifactUnavailableError(FileNotFoundError):
    """Raised when the approved private model artifact is unavailable."""


class ModelArtifactIntegrityError(ValueError):
    """Raised when an artifact does not match its approved SHA-256."""


@dataclass(frozen=True, slots=True)
class TerrainInputMetadata:
    """Coordinate-free metadata required before reading a terrain patch."""

    crs: str | None
    width: int
    height: int
    resolution_m: tuple[float, float]
    band_count: int
    nodata_fraction: float


@dataclass(frozen=True, slots=True)
class TerrainInputContract:
    """Exact Phase 5 single-patch input requirements; no silent reprojection."""

    crs: str
    width: int
    height: int
    resolution_m: float
    band_count: int
    maximum_nodata_fraction: float

    def validate(self, metadata: TerrainInputMetadata) -> None:
        if not isinstance(metadata, TerrainInputMetadata):
            raise TerrainInputValidationError("metadata_type_invalid")
        reasons: list[str] = []
        try:
            crs_matches = isinstance(metadata.crs, str) and CRS.from_user_input(
                metadata.crs
            ) == CRS.from_user_input(self.crs)
        except (TypeError, ValueError):
            crs_matches = False
        if not crs_matches:
            reasons.append("crs_mismatch_no_automatic_reprojection")
        dimensions_are_integers = all(
            isinstance(value, int) and not isinstance(value, bool)
            for value in (metadata.width, metadata.height)
        )
        if not dimensions_are_integers or (metadata.width, metadata.height) != (
            self.width,
            self.height,
        ):
            reasons.append("dimensions_mismatch")
        resolution_is_numeric_pair = (
            isinstance(metadata.resolution_m, tuple)
            and len(metadata.resolution_m) == 2
            and all(
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
                for value in metadata.resolution_m
            )
        )
        if not resolution_is_numeric_pair or any(
            not math.isclose(value, self.resolution_m, abs_tol=1e-6)
            for value in metadata.resolution_m
        ):
            reasons.append("resolution_mismatch")
        if (
            not isinstance(metadata.band_count, int)
            or isinstance(metadata.band_count, bool)
            or metadata.band_count != self.band_count
        ):
            reasons.append("band_count_mismatch")
        if (
            not isinstance(metadata.nodata_fraction, (int, float))
            or isinstance(metadata.nodata_fraction, bool)
            or not math.isfinite(metadata.nodata_fraction)
            or not 0 <= metadata.nodata_fraction <= self.maximum_nodata_fraction
        ):
            reasons.append("nodata_policy_failed")
        if reasons:
            raise TerrainInputValidationError(",".join(reasons))


E001_TERRAIN_INPUT = TerrainInputContract(
    crs="EPSG:27700",
    width=128,
    height=128,
    resolution_m=1.0,
    band_count=1,
    maximum_nodata_fraction=0.2,
)


def _validate_sha256(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or not SHA256_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")


def _validate_code_tuple(
    value: object,
    *,
    field_name: str,
    code_type: type[WarningCode] | type[LimitationCode],
    required: frozenset[WarningCode] | frozenset[LimitationCode],
) -> None:
    if not isinstance(value, tuple) or any(not isinstance(item, code_type) for item in value):
        raise TypeError(f"{field_name} must be a tuple of approved {code_type.__name__} values")
    if len(value) != len(set(value)):
        raise ValueError(f"{field_name} cannot contain duplicate codes")
    missing = required.difference(value)
    if missing:
        raise ValueError(f"{field_name} is missing required safety codes")


@dataclass(frozen=True, slots=True)
class AutomaticInferenceResult:
    """Coordinate-safe result envelope for a future automatic inference path."""

    terrain_similarity_score: float
    evidence_level: EvidenceLevel
    model_identifier: ModelIdentifier
    model_config_sha256: str
    warnings: tuple[WarningCode, ...] = (
        WarningCode.HUMAN_REVIEW_REQUIRED,
        WarningCode.AUTOMATIC_EVIDENCE_ONLY,
    )
    limitations: tuple[LimitationCode, ...] = (
        LimitationCode.NOT_ARCHAEOLOGICAL_PROBABILITY,
        LimitationCode.NOT_ARCHAEOLOGICAL_CONFIRMATION,
        LimitationCode.E001_SCOPE_ONLY,
    )
    private_metadata: Mapping[str, Any] = field(default_factory=dict, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.evidence_level, EvidenceLevel):
            raise TypeError("evidence_level must be an EvidenceLevel")
        if self.evidence_level not in AUTOMATIC_EVIDENCE_LEVELS:
            raise ValueError("automatic inference cannot assert human or archaeological review")
        if (
            not isinstance(self.terrain_similarity_score, float)
            or not math.isfinite(self.terrain_similarity_score)
            or not (0 <= self.terrain_similarity_score <= 1)
        ):
            raise ValueError("terrain_similarity_score must be a finite float within [0, 1]")
        if (
            not isinstance(self.model_identifier, str)
            or len(self.model_identifier) > MAXIMUM_MODEL_IDENTIFIER_LENGTH
            or not MODEL_IDENTIFIER_PATTERN.fullmatch(self.model_identifier)
        ):
            raise ValueError(
                "model_identifier must be a 1-64 character lowercase alphanumeric hyphen slug"
            )
        if not isinstance(self.model_identifier, ModelIdentifier):
            raise TypeError("model_identifier must be an approved ModelIdentifier")
        _validate_sha256(self.model_config_sha256, field_name="model_config_sha256")
        if self.model_config_sha256 != APPROVED_MODEL_CONFIG_SHA256[self.model_identifier]:
            raise ValueError("model_config_sha256 does not match the approved model identifier")
        _validate_code_tuple(
            self.warnings,
            field_name="warnings",
            code_type=WarningCode,
            required=REQUIRED_WARNING_CODES,
        )
        _validate_code_tuple(
            self.limitations,
            field_name="limitations",
            code_type=LimitationCode,
            required=REQUIRED_LIMITATION_CODES,
        )
        if not isinstance(self.private_metadata, Mapping):
            raise TypeError("private_metadata must be a mapping")

    def to_public_dict(self) -> dict[str, object]:
        """Serialize through an allowlist that excludes all private request context."""
        return {
            "schema_version": "archaeoai-inference-result-v1",
            "evidence_level": self.evidence_level.value,
            "terrain_similarity_score": self.terrain_similarity_score,
            "score_semantics": SCORE_SEMANTICS,
            "model_identifier": self.model_identifier.value,
            "model_config_sha256": self.model_config_sha256,
            "warnings": [WARNING_MESSAGES[code] for code in self.warnings],
            "limitations": [LIMITATION_MESSAGES[code] for code in self.limitations],
        }


def verify_model_artifact_checksum(path: str | Path, *, expected_sha256: str) -> str:
    """Verify availability and integrity without deserializing or executing the model.

    There is intentionally no training fallback. A missing or changed artifact is a hard
    stop that must be resolved through a separately authorized artifact process.
    """
    _validate_sha256(expected_sha256, field_name="expected_sha256")
    source = Path(path)
    if not source.is_file():
        raise ModelArtifactUnavailableError(
            "approved model artifact is unavailable; automatic retraining is prohibited"
        )
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    observed = digest.hexdigest()
    if observed != expected_sha256:
        raise ModelArtifactIntegrityError("approved model artifact SHA-256 mismatch")
    return observed

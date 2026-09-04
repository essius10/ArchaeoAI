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
from typing import Any

from pyproj import CRS

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SCORE_SEMANTICS = "terrain_pattern_similarity_not_archaeological_probability"


class EvidenceLevel(StrEnum):
    """Evidence ladder; automatic inference is restricted to its first two levels."""

    AI_OUTPUT = "AI_OUTPUT"
    AI_HYPOTHESIS = "AI_HYPOTHESIS"
    HUMAN_REVIEWED_TERRAIN_FEATURE = "HUMAN_REVIEWED_TERRAIN_FEATURE"
    ARCHAEOLOGIST_REVIEWED_FEATURE = "ARCHAEOLOGIST_REVIEWED_FEATURE"
    CONFIRMED_ARCHAEOLOGICAL_SITE = "CONFIRMED_ARCHAEOLOGICAL_SITE"


AUTOMATIC_EVIDENCE_LEVELS = frozenset(
    {
        EvidenceLevel.AI_OUTPUT,
        EvidenceLevel.AI_HYPOTHESIS,
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
        reasons: list[str] = []
        try:
            crs_matches = metadata.crs is not None and CRS.from_user_input(
                metadata.crs
            ) == CRS.from_user_input(self.crs)
        except (TypeError, ValueError):
            crs_matches = False
        if not crs_matches:
            reasons.append("crs_mismatch_no_automatic_reprojection")
        if (metadata.width, metadata.height) != (self.width, self.height):
            reasons.append("dimensions_mismatch")
        if len(metadata.resolution_m) != 2 or any(
            not math.isfinite(value) or not math.isclose(value, self.resolution_m, abs_tol=1e-6)
            for value in metadata.resolution_m
        ):
            reasons.append("resolution_mismatch")
        if metadata.band_count != self.band_count:
            reasons.append("band_count_mismatch")
        if (
            not math.isfinite(metadata.nodata_fraction)
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
    if not SHA256_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")


@dataclass(frozen=True, slots=True)
class AutomaticInferenceResult:
    """Coordinate-safe result envelope for a future automatic inference path."""

    terrain_similarity_score: float
    evidence_level: EvidenceLevel
    model_identifier: str
    model_config_sha256: str
    warnings: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    private_metadata: Mapping[str, Any] = field(default_factory=dict, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.evidence_level not in AUTOMATIC_EVIDENCE_LEVELS:
            raise ValueError("automatic inference cannot assert human or archaeological review")
        if not math.isfinite(self.terrain_similarity_score) or not (
            0 <= self.terrain_similarity_score <= 1
        ):
            raise ValueError("terrain_similarity_score must be finite and within [0, 1]")
        if not self.model_identifier.strip():
            raise ValueError("model_identifier cannot be empty")
        _validate_sha256(self.model_config_sha256, field_name="model_config_sha256")

    def to_public_dict(self) -> dict[str, object]:
        """Serialize through an allowlist that excludes all private request context."""
        return {
            "schema_version": "archaeoai-inference-result-v1",
            "evidence_level": self.evidence_level.value,
            "terrain_similarity_score": self.terrain_similarity_score,
            "score_semantics": SCORE_SEMANTICS,
            "model_identifier": self.model_identifier,
            "model_config_sha256": self.model_config_sha256,
            "warnings": list(self.warnings),
            "limitations": list(self.limitations),
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

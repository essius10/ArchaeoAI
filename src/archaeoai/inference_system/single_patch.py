"""Synthetic-tested, single-patch feature and model-adapter boundary.

This module reuses the frozen Phase 2F feature implementation. It does not read
terrain files, load or deserialize a model, fit anything, or provide a fallback
score. The model adapter is exercised only with inert doubles in Phase 5B tests.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import numpy as np

from archaeoai.inference import (
    FEATURE_COUNT,
    PATCH_SIZE_PIXELS,
    REPRESENTATION_CHANNELS,
    features_from_elevation,
)
from archaeoai.inference_system.contracts import (
    APPROVED_MODEL_CONFIG_SHA256,
    E001_TERRAIN_INPUT,
    AutomaticInferenceResult,
    EvidenceLevel,
    ModelIdentifier,
    TerrainInputMetadata,
    TerrainInputValidationError,
    verify_model_artifact_checksum,
)
from archaeoai.terrain.privacy import ensure_private_output

APPROVED_MODEL_ARTIFACT_SHA256 = "50f7968069ecaa1e0016f37be6356531ab3f26802c806efb5dc8fb2e295a503f"
APPROVED_MODEL_RELATIVE_PATH = Path("data/private/e001/inference/e001_phase2f_random_forest.pkl")


class SinglePatchValidationError(TerrainInputValidationError):
    """Raised when patch values conflict with the frozen input contract."""


class ModelAdapterUnavailableError(RuntimeError):
    """Raised when no explicit, compatible model adapter is supplied."""


class ModelAdapterOutputError(ValueError):
    """Raised when an adapter returns an invalid terrain-similarity score."""


class ModelAdapterIdentityError(ValueError):
    """Raised when an adapter is not bound to the one approved model identity."""


class SinglePatchModelAdapter(Protocol):
    """Minimal future model boundary; Phase 5B uses only inert test doubles."""

    model_identifier: ModelIdentifier
    model_config_sha256: str
    model_artifact_sha256: str

    def score_model_input(self, feature_matrix: np.ndarray) -> float:
        """Return one bounded terrain-pattern-similarity score."""


@dataclass(frozen=True, slots=True)
class TerrainPatch:
    """One coordinate-free terrain array and its explicit metadata."""

    elevation: np.ndarray = field(repr=False)
    mask: np.ndarray = field(repr=False)
    metadata: TerrainInputMetadata


@dataclass(frozen=True, slots=True)
class SinglePatchFeatures:
    """Immutable-view result of the canonical four-channel feature transform."""

    feature_vector: np.ndarray = field(repr=False)
    representation_names: tuple[str, ...] = REPRESENTATION_CHANNELS

    def model_input(self) -> np.ndarray:
        """Return the exact one-row matrix shape expected immediately before scoring."""
        matrix = self.feature_vector.reshape(1, FEATURE_COUNT)
        matrix.setflags(write=False)
        return matrix


@dataclass(frozen=True, slots=True)
class ApprovedModelArtifactReference:
    """Public identity bindings plus a non-serialized private artifact path."""

    path: Path = field(repr=False)
    model_identifier: ModelIdentifier
    model_config_sha256: str


def _validate_patch_arrays(patch: TerrainPatch) -> tuple[np.ndarray, np.ndarray]:
    if not isinstance(patch.elevation, np.ndarray):
        raise SinglePatchValidationError("elevation_must_be_numpy_array")
    if patch.elevation.ndim != 2:
        raise SinglePatchValidationError("elevation_dimensions_mismatch")
    if patch.elevation.shape != (PATCH_SIZE_PIXELS, PATCH_SIZE_PIXELS):
        raise SinglePatchValidationError("elevation_shape_mismatch")
    if patch.elevation.dtype.kind not in "iuf":
        raise SinglePatchValidationError("elevation_dtype_must_be_real_numeric")
    if not isinstance(patch.mask, np.ndarray) or patch.mask.dtype != np.bool_:
        raise SinglePatchValidationError("mask_must_be_boolean_numpy_array")
    if patch.mask.ndim != 2 or patch.mask.shape != patch.elevation.shape:
        raise SinglePatchValidationError("mask_shape_mismatch")

    values = np.asarray(patch.elevation, dtype=np.float32)
    mask = np.asarray(patch.mask, dtype=bool)
    if np.any(~np.isfinite(values) & ~mask):
        raise SinglePatchValidationError("unmasked_nan_or_infinity")
    observed_nodata_fraction = float(np.count_nonzero(mask) / mask.size)
    if not math.isclose(
        observed_nodata_fraction,
        float(patch.metadata.nodata_fraction),
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise SinglePatchValidationError("nodata_fraction_metadata_mismatch")
    return values, mask


def transform_single_patch(patch: TerrainPatch) -> SinglePatchFeatures:
    """Validate and transform one patch through the canonical research feature path."""
    if not isinstance(patch, TerrainPatch):
        raise SinglePatchValidationError("terrain_patch_type_invalid")
    E001_TERRAIN_INPUT.validate(patch.metadata)
    values, mask = _validate_patch_arrays(patch)
    feature_vector = features_from_elevation(
        values,
        mask,
        resolution_m=E001_TERRAIN_INPUT.resolution_m,
    )
    if feature_vector.dtype != np.float32 or feature_vector.shape != (FEATURE_COUNT,):
        raise SinglePatchValidationError("canonical_feature_contract_mismatch")
    feature_vector.setflags(write=False)
    return SinglePatchFeatures(feature_vector=feature_vector)


def verify_approved_model_artifact(
    project_root: Path,
    reference: ApprovedModelArtifactReference,
) -> str:
    """Verify the one approved private artifact identity and bytes without loading it."""
    if not isinstance(reference, ApprovedModelArtifactReference):
        raise TypeError("reference must be an ApprovedModelArtifactReference")
    if not isinstance(reference.model_identifier, ModelIdentifier):
        raise ValueError("unapproved model identity")
    approved_config = APPROVED_MODEL_CONFIG_SHA256.get(reference.model_identifier)
    if reference.model_config_sha256 != approved_config:
        raise ValueError("model configuration identity mismatch")

    root = Path(project_root).resolve()
    approved_path = (root / APPROVED_MODEL_RELATIVE_PATH).resolve()
    candidate = ensure_private_output(root, reference.path)
    if candidate != approved_path:
        raise ValueError("unexpected private model artifact path")
    return verify_model_artifact_checksum(
        candidate,
        expected_sha256=APPROVED_MODEL_ARTIFACT_SHA256,
    )


def score_single_patch_model_adapter(
    features: SinglePatchFeatures,
    adapter: SinglePatchModelAdapter | None,
) -> float:
    """Exercise the model-input plumbing without asserting a production model identity."""
    if not isinstance(features, SinglePatchFeatures):
        raise TypeError("features must be SinglePatchFeatures")
    vector = features.feature_vector
    if (
        not isinstance(vector, np.ndarray)
        or vector.shape != (FEATURE_COUNT,)
        or vector.dtype != np.float32
        or not np.isfinite(vector).all()
        or vector.flags.writeable
        or not vector.flags.c_contiguous
        or features.representation_names != REPRESENTATION_CHANNELS
    ):
        raise ValueError("model adapter requires the frozen finite float32 feature vector")
    if adapter is None or not callable(getattr(adapter, "score_model_input", None)):
        raise ModelAdapterUnavailableError("an explicit approved model adapter is required")
    if (
        getattr(adapter, "model_identifier", None) is not ModelIdentifier.E001_FROZEN_RANDOM_FOREST
        or getattr(adapter, "model_config_sha256", None)
        != APPROVED_MODEL_CONFIG_SHA256[ModelIdentifier.E001_FROZEN_RANDOM_FOREST]
        or getattr(adapter, "model_artifact_sha256", None) != APPROVED_MODEL_ARTIFACT_SHA256
    ):
        raise ModelAdapterIdentityError("model adapter identity binding mismatch")
    score = adapter.score_model_input(features.model_input())
    if not isinstance(score, float) or not math.isfinite(score) or not 0 <= score <= 1:
        raise ModelAdapterOutputError("adapter score must be a finite float within [0, 1]")
    return score


def run_approved_single_patch_inference(
    project_root: Path,
    reference: ApprovedModelArtifactReference,
    features: SinglePatchFeatures,
    adapter: SinglePatchModelAdapter | None,
) -> AutomaticInferenceResult:
    """Build a public result only after the approved private artifact gate passes.

    Phase 5B does not call this successful path because it neither loads nor executes
    the approved model. A later authorized loader may supply the adapter only after
    verifying the exact private artifact through this boundary.
    """
    verify_approved_model_artifact(project_root, reference)
    score = score_single_patch_model_adapter(features, adapter)
    model_identifier = ModelIdentifier.E001_FROZEN_RANDOM_FOREST
    return AutomaticInferenceResult(
        terrain_similarity_score=score,
        evidence_level=EvidenceLevel.AI_OUTPUT,
        model_identifier=model_identifier,
        model_config_sha256=APPROVED_MODEL_CONFIG_SHA256[model_identifier],
    )

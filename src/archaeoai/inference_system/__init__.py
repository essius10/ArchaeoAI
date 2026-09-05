"""Public, fail-closed contracts for future ArchaeoAI inference interfaces.

This package does not load or execute a model. The Phase 2F research engine remains
separate until a later, explicitly approved implementation phase.
"""

from archaeoai.inference_system.contracts import (
    E001_TERRAIN_INPUT,
    AutomaticInferenceResult,
    EvidenceLevel,
    LimitationCode,
    ModelArtifactIntegrityError,
    ModelArtifactUnavailableError,
    ModelIdentifier,
    TerrainInputContract,
    TerrainInputMetadata,
    WarningCode,
    verify_model_artifact_checksum,
)
from archaeoai.inference_system.single_patch import (
    APPROVED_MODEL_ARTIFACT_SHA256,
    APPROVED_MODEL_RELATIVE_PATH,
    ApprovedModelArtifactReference,
    ModelAdapterIdentityError,
    ModelAdapterOutputError,
    ModelAdapterUnavailableError,
    SinglePatchFeatures,
    SinglePatchModelAdapter,
    SinglePatchValidationError,
    TerrainPatch,
    run_approved_single_patch_inference,
    score_single_patch_model_adapter,
    transform_single_patch,
    verify_approved_model_artifact,
)

__all__ = [
    "E001_TERRAIN_INPUT",
    "APPROVED_MODEL_ARTIFACT_SHA256",
    "APPROVED_MODEL_RELATIVE_PATH",
    "ApprovedModelArtifactReference",
    "AutomaticInferenceResult",
    "EvidenceLevel",
    "LimitationCode",
    "ModelArtifactIntegrityError",
    "ModelArtifactUnavailableError",
    "ModelAdapterIdentityError",
    "ModelIdentifier",
    "ModelAdapterOutputError",
    "ModelAdapterUnavailableError",
    "SinglePatchFeatures",
    "SinglePatchModelAdapter",
    "SinglePatchValidationError",
    "TerrainInputContract",
    "TerrainInputMetadata",
    "TerrainPatch",
    "WarningCode",
    "verify_model_artifact_checksum",
    "run_approved_single_patch_inference",
    "score_single_patch_model_adapter",
    "transform_single_patch",
    "verify_approved_model_artifact",
]

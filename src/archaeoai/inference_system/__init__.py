"""Public, fail-closed contracts for future ArchaeoAI inference interfaces.

This package does not load or execute a model. The Phase 2F research engine remains
separate until a later, explicitly approved implementation phase.
"""

from archaeoai.inference_system.contracts import (
    E001_TERRAIN_INPUT,
    AutomaticInferenceResult,
    EvidenceLevel,
    ModelArtifactIntegrityError,
    ModelArtifactUnavailableError,
    TerrainInputContract,
    TerrainInputMetadata,
    verify_model_artifact_checksum,
)

__all__ = [
    "E001_TERRAIN_INPUT",
    "AutomaticInferenceResult",
    "EvidenceLevel",
    "ModelArtifactIntegrityError",
    "ModelArtifactUnavailableError",
    "TerrainInputContract",
    "TerrainInputMetadata",
    "verify_model_artifact_checksum",
]

"""Hash-bound loader and adapter for the one approved private E001 model."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier

from archaeoai.inference import FEATURE_COUNT, load_private_model, model_state_sha256
from archaeoai.inference import score_feature_matrix as score_frozen_feature_matrix
from archaeoai.inference_system.contracts import (
    APPROVED_MODEL_CONFIG_SHA256,
    ModelIdentifier,
)
from archaeoai.inference_system.single_patch import (
    APPROVED_MODEL_ARTIFACT_SHA256,
    APPROVED_MODEL_RELATIVE_PATH,
    ApprovedModelArtifactReference,
    verify_approved_model_artifact,
)
from archaeoai.terrain.privacy import ensure_private_output, verify_git_ignored

FROZEN_MODEL_STATE_SHA256 = "e3b0c072f437e889f09a2a2cf5a37f19b2f483eb5188e102b132a89ee76d1939"


class ApprovedPrivateModelLoadError(RuntimeError):
    """Safe public failure for an unavailable or invalid approved model runtime."""

    code = "APPROVED_PRIVATE_MODEL_UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class ApprovedPrivateRandomForestAdapter:
    """Expose only frozen single-patch scoring from a verified private estimator."""

    _estimator: RandomForestClassifier = field(repr=False)
    model_identifier: ModelIdentifier = ModelIdentifier.E001_FROZEN_RANDOM_FOREST
    model_config_sha256: str = APPROVED_MODEL_CONFIG_SHA256[
        ModelIdentifier.E001_FROZEN_RANDOM_FOREST
    ]
    model_artifact_sha256: str = APPROVED_MODEL_ARTIFACT_SHA256

    def __post_init__(self) -> None:
        if self.model_identifier is not ModelIdentifier.E001_FROZEN_RANDOM_FOREST:
            raise ValueError("approved private model identifier mismatch")
        if self.model_config_sha256 != APPROVED_MODEL_CONFIG_SHA256[self.model_identifier]:
            raise ValueError("approved private model configuration identity mismatch")
        if self.model_artifact_sha256 != APPROVED_MODEL_ARTIFACT_SHA256:
            raise ValueError("approved private model artifact identity mismatch")
        if type(self._estimator) is not RandomForestClassifier:
            raise TypeError("approved adapter requires the exact RandomForestClassifier class")
        if model_state_sha256(self._estimator) != FROZEN_MODEL_STATE_SHA256:
            raise ValueError("approved private model state mismatch")

    def score_model_input(self, feature_matrix: np.ndarray) -> float:
        """Score one immutable frozen feature row through the canonical implementation."""
        if (
            not isinstance(feature_matrix, np.ndarray)
            or feature_matrix.shape != (1, FEATURE_COUNT)
            or feature_matrix.dtype != np.float32
            or feature_matrix.flags.writeable
            or not feature_matrix.flags.c_contiguous
            or not np.isfinite(feature_matrix).all()
        ):
            raise ValueError("approved model input contract mismatch")
        scores = score_frozen_feature_matrix(self._estimator, feature_matrix)
        if scores.shape != (1,) or not math.isfinite(float(scores[0])) or not 0 <= scores[0] <= 1:
            raise ValueError("approved model output contract mismatch")
        return float(scores[0])


def approved_private_model_reference(project_root: Path) -> ApprovedModelArtifactReference:
    """Build the only authorized reference without accepting a caller-supplied path."""
    root = Path(project_root).resolve()
    return ApprovedModelArtifactReference(
        path=root / APPROVED_MODEL_RELATIVE_PATH,
        model_identifier=ModelIdentifier.E001_FROZEN_RANDOM_FOREST,
        model_config_sha256=APPROVED_MODEL_CONFIG_SHA256[ModelIdentifier.E001_FROZEN_RANDOM_FOREST],
    )


def load_approved_private_random_forest(
    project_root: Path,
) -> ApprovedPrivateRandomForestAdapter:
    """Verify every approved identity before allowing private pickle deserialization."""
    root = Path(project_root).resolve()
    reference = approved_private_model_reference(root)
    try:
        private_path = ensure_private_output(root, reference.path)
        if private_path != (root / APPROVED_MODEL_RELATIVE_PATH).resolve():
            raise ValueError("unexpected approved model path")
        verify_git_ignored(root, private_path)
        verified_artifact_sha256 = verify_approved_model_artifact(root, reference)
        if verified_artifact_sha256 != APPROVED_MODEL_ARTIFACT_SHA256:
            raise ValueError("approved model artifact identity mismatch")
        estimator = load_private_model(
            root,
            private_path,
            expected_artifact_sha256=APPROVED_MODEL_ARTIFACT_SHA256,
            expected_state_sha256=FROZEN_MODEL_STATE_SHA256,
        )
        if type(estimator) is not RandomForestClassifier:
            raise ValueError("approved model class mismatch")
        if model_state_sha256(estimator) != FROZEN_MODEL_STATE_SHA256:
            raise ValueError("approved model state mismatch")
        return ApprovedPrivateRandomForestAdapter(estimator)
    except ApprovedPrivateModelLoadError:
        raise
    except Exception as exc:
        raise ApprovedPrivateModelLoadError(ApprovedPrivateModelLoadError.code) from exc

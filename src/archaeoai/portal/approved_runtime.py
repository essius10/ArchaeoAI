"""Approved frozen E001 model execution over mathematical synthetic terrain only."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from archaeoai.inference import FEATURE_COUNT
from archaeoai.inference_system import (
    APPROVED_MODEL_ARTIFACT_SHA256,
    FROZEN_MODEL_STATE_SHA256,
    ApprovedPrivateRandomForestAdapter,
    TerrainInputMetadata,
    TerrainPatch,
    approved_private_model_reference,
    run_approved_single_patch_inference,
    transform_single_patch,
)
from archaeoai.inference_system.contracts import (
    APPROVED_MODEL_CONFIG_SHA256,
    ModelIdentifier,
)
from archaeoai.portal.demo_runtime import SyntheticDemoRuntime
from archaeoai.portal.model_runtime import ApprovedModelRuntimeExecutionError, RuntimeResult
from archaeoai.portal.schemas import EvidenceLevel, SyntheticScenario


@dataclass(frozen=True, slots=True)
class ApprovedPrivateRandomForestRuntime:
    """Server-authorized real model runtime with no file or coordinate input surface."""

    project_root: Path = field(repr=False)
    adapter: ApprovedPrivateRandomForestAdapter = field(repr=False)
    runtime_name: str = "APPROVED_PRIVATE_RANDOM_FOREST"
    result_count: int = 6

    def validate(self) -> None:
        if self.adapter.model_identifier is not ModelIdentifier.E001_FROZEN_RANDOM_FOREST:
            raise ApprovedModelRuntimeExecutionError(ApprovedModelRuntimeExecutionError.code)
        if self.adapter.model_artifact_sha256 != APPROVED_MODEL_ARTIFACT_SHA256:
            raise ApprovedModelRuntimeExecutionError(ApprovedModelRuntimeExecutionError.code)

    def public_status(self) -> dict[str, object]:
        return {
            "runtime_mode": "APPROVED_PRIVATE_MODEL",
            "approved_runtime_enabled": True,
            "artifact_verified": True,
            "model_execution_available": True,
            "model_identifier": self.adapter.model_identifier.value,
            "model_config_sha256": APPROVED_MODEL_CONFIG_SHA256[
                ModelIdentifier.E001_FROZEN_RANDOM_FOREST
            ],
            "model_state_sha256": FROZEN_MODEL_STATE_SHA256,
            "input_mode": "SYNTHETIC_ONLY",
        }

    def screen(self, scenario: SyntheticScenario, count: int = 6) -> tuple[RuntimeResult, ...]:
        if count != self.result_count:
            raise ValueError("approved synthetic result count is fixed")
        self.validate()
        reference = approved_private_model_reference(self.project_root)
        results: list[RuntimeResult] = []
        try:
            for variant in range(count):
                elevation = SyntheticDemoRuntime.surface(scenario, variant)
                features = transform_single_patch(
                    TerrainPatch(
                        elevation=elevation,
                        mask=np.zeros_like(elevation, dtype=bool),
                        metadata=TerrainInputMetadata(
                            crs="EPSG:27700",
                            width=128,
                            height=128,
                            resolution_m=(1.0, 1.0),
                            band_count=1,
                            nodata_fraction=0.0,
                        ),
                    )
                )
                if features.feature_vector.shape != (FEATURE_COUNT,):
                    raise ValueError("canonical feature contract failed")
                inference = run_approved_single_patch_inference(
                    self.project_root,
                    reference,
                    features,
                    self.adapter,
                )
                score = inference.terrain_similarity_score
                priority = (
                    "HIGHER_REVIEW_PRIORITY"
                    if score >= 0.66
                    else "STANDARD_REVIEW_PRIORITY"
                    if score >= 0.4
                    else "LOWER_REVIEW_PRIORITY"
                )
                results.append(
                    RuntimeResult(
                        score=score,
                        priority=priority,
                        evidence_level=EvidenceLevel.AI_OUTPUT,
                        thumbnail_id=f"synthetic-{scenario.value.casefold()}-{variant + 1}",
                        warning_code="HUMAN_REVIEW_REQUIRED",
                        limitation_code="TERRAIN_SIMILARITY_NOT_ARCHAEOLOGICAL_PROBABILITY",
                        runtime=self.runtime_name,
                        model_execution="PERFORMED_APPROVED_PRIVATE_MODEL",
                    )
                )
                del features, elevation
        except Exception as exc:
            raise ApprovedModelRuntimeExecutionError(
                ApprovedModelRuntimeExecutionError.code
            ) from exc
        return tuple(results)

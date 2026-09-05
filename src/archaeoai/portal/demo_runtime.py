"""Deterministic mathematical terrain demonstration using the canonical Phase 5 transform."""

from __future__ import annotations

import hashlib

import numpy as np

from archaeoai.inference import FEATURE_COUNT
from archaeoai.inference_system import TerrainInputMetadata, TerrainPatch, transform_single_patch
from archaeoai.portal.model_runtime import RuntimeResult
from archaeoai.portal.schemas import EvidenceLevel, SyntheticScenario


class SyntheticDemoRuntime:
    """Generate synthetic UI records without a model or archaeological inference."""

    runtime_name = "SYNTHETIC_DEMO"
    result_count = 6

    @staticmethod
    def surface(scenario: SyntheticScenario, variant: int) -> np.ndarray:
        y, x = np.mgrid[-64:64, -64:64]
        phase = variant * 0.37
        if scenario is SyntheticScenario.MOUND_LIKE:
            values = 100 + (1.1 + variant * 0.06) * np.exp(
                -(((x - variant) ** 2 + (y + variant) ** 2) / (260 + variant * 18))
            )
        elif scenario is SyntheticScenario.DEPRESSION_LIKE:
            values = 100 - (0.8 + variant * 0.05) * np.exp(
                -(((x + variant) ** 2 + (y - variant) ** 2) / (320 + variant * 20))
            )
        elif scenario is SyntheticScenario.PLANAR:
            values = 100 + (0.008 + variant * 0.001) * x + 0.006 * y
        elif scenario is SyntheticScenario.SINUSOIDAL:
            values = (
                100 + 0.25 * np.sin(x / (7 + variant * 0.2) + phase) + 0.18 * np.cos(y / 9 - phase)
            )
        else:
            values = (
                100
                + 0.55 * np.exp(-((x**2 + y**2) / 300))
                + 0.18 * np.sin((x + variant) / 8)
                - 0.12 * np.cos((y - variant) / 11)
            )
        return np.asarray(values, dtype=np.float32)

    @staticmethod
    def _demonstration_score(scenario: SyntheticScenario, variant: int) -> float:
        digest = hashlib.sha256(f"phase6c:{scenario.value}:{variant}".encode()).digest()
        unit = int.from_bytes(digest[:4], "big") / 0xFFFFFFFF
        return round(0.18 + 0.72 * unit, 4)

    def screen(self, scenario: SyntheticScenario, count: int = 6) -> tuple[RuntimeResult, ...]:
        if count != self.result_count:
            raise ValueError("synthetic demonstration count is fixed")
        results: list[RuntimeResult] = []
        for variant in range(count):
            elevation = self.surface(scenario, variant)
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
                raise RuntimeError("canonical feature contract failed")
            score = self._demonstration_score(scenario, variant)
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
                    evidence_level=EvidenceLevel.AI_HYPOTHESIS,
                    thumbnail_id=f"synthetic-{scenario.value.casefold()}-{variant + 1}",
                    warning_code="HUMAN_REVIEW_REQUIRED",
                    limitation_code="SYNTHETIC_DEMONSTRATION_NOT_ARCHAEOLOGICAL_INFERENCE",
                    runtime=self.runtime_name,
                    model_execution="NOT_PERFORMED",
                )
            )
            del features, elevation
        return tuple(results)

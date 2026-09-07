"""Portal screening-runtime boundary; the approved runtime is intentionally disabled."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from archaeoai.portal.schemas import EvidenceLevel, SyntheticScenario


@dataclass(frozen=True, slots=True)
class RuntimeResult:
    score: float
    priority: str
    evidence_level: EvidenceLevel
    thumbnail_id: str
    warning_code: str
    limitation_code: str
    runtime: str
    model_execution: str


class ScreeningRuntime(Protocol):
    runtime_name: str

    def screen(self, scenario: SyntheticScenario, count: int = 6) -> tuple[RuntimeResult, ...]:
        """Return bounded automatic screening records."""


class ApprovedModelRuntimeNotAuthorizedError(RuntimeError):
    """Raised before any artifact lookup, loading, deserialization, or execution."""

    code = "APPROVED_MODEL_RUNTIME_NOT_AUTHORIZED"


class DisabledApprovedModelRuntime:
    """Hard-stop production adapter for Phase 6C."""

    runtime_name = "APPROVED_MODEL_DISABLED"
    code = ApprovedModelRuntimeNotAuthorizedError.code

    def screen(self, scenario: SyntheticScenario, count: int = 6) -> tuple[RuntimeResult, ...]:
        del scenario, count
        raise ApprovedModelRuntimeNotAuthorizedError(self.code)

    def validate(self) -> None:
        raise ApprovedModelRuntimeNotAuthorizedError(self.code)

import json
import subprocess
from pathlib import Path

from archaeoai.inference import validate_inference_protocol
from archaeoai.manuscript import EXPECTED_MANUSCRIPT_EVIDENCE_SHA256, validate_manuscript_evidence
from archaeoai.model_data import validate_frozen_primary_config

ROOT = Path(__file__).resolve().parents[1]
ARCHITECTURE = ROOT / "docs/architecture/PHASE_5_INFERENCE_ARCHITECTURE.md"
CLASSIFICATION = "INFERENCE_CODE_READY_MODEL_ARTIFACT_UNAVAILABLE"
RQ1_STATUS = "RQ1_PROVISIONALLY_ANSWERED_PENDING_REVIEW"


def test_phase5a_records_exact_readiness_classification_and_boundaries() -> None:
    text = ARCHITECTURE.read_text(encoding="utf-8")
    assert f"**B — `{CLASSIFICATION}`.**" in text
    assert RQ1_STATUS in text
    assert "An automatic inference path may emit only levels 1–2" in text
    assert "Phase 5A does not train, tune, score" in text


def test_phase5a_preserves_frozen_model_protocol_and_manuscript() -> None:
    config = validate_frozen_primary_config(
        ROOT / "outputs/modelling/e001_primary_baseline_config.json"
    )
    protocol = validate_inference_protocol(ROOT / "configs/e001-phase-2f-a-inference-protocol.json")
    manuscript = validate_manuscript_evidence(
        ROOT / "outputs/manuscript/e001_manuscript_evidence.json", root=ROOT
    )
    assert config["config_sha256"] == (
        "20cd377c17373eeeb5403c84119084287f193d93b42c8004d99c823e01a157e4"
    )
    assert protocol["protocol_sha256"] == (
        "fa1f9cd12230df3f7c83c45febd5ec0ba751f371a098600873380bc47c624095"
    )
    assert manuscript["evidence_manifest_sha256"] == EXPECTED_MANUSCRIPT_EVIDENCE_SHA256


def test_status_documents_do_not_promote_contracts_into_capability() -> None:
    texts = [
        (ROOT / path).read_text(encoding="utf-8")
        for path in ("README.md", "docs/CURRENT_STATUS.md", "docs/roadmap.md")
    ]
    combined = "\n".join(texts)
    assert CLASSIFICATION in combined
    assert RQ1_STATUS in combined
    assert "no model was loaded or\nexecuted" in combined.lower()
    assert "no archaeological discovery claim" in combined.lower()


def test_no_model_or_checkpoint_artifact_is_tracked() -> None:
    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    forbidden_suffixes = (".pkl", ".pickle", ".joblib", ".onnx", ".pt", ".pth", ".ckpt")
    assert not [path for path in tracked if path.casefold().endswith(forbidden_suffixes)]


def test_phase5a_architecture_preserves_its_historical_no_interface_boundary() -> None:
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    architecture = ARCHITECTURE.read_text(encoding="utf-8")
    assert "No CLI or API is added in Phase 5A" in architecture
    assert "[project.scripts]" in project
    assert 'archaeoai = "archaeoai.cli:main"' in project
    assert not (ROOT / "src/archaeoai/inference_system/api.py").exists()
    assert not (ROOT / "src/archaeoai/inference_system/cli.py").exists()


def test_phase5a_public_contract_contains_no_scientific_result_payload() -> None:
    source = (ROOT / "src/archaeoai/inference_system/contracts.py").read_text(encoding="utf-8")
    result = json.loads(
        (ROOT / "outputs/external_validation/e001_phase3c_external_evaluation.json").read_text(
            encoding="utf-8"
        )
    )
    assert result["external_test_spent"] is True
    for forbidden in ("balanced_accuracy", "roc_auc", "average_precision", "confusion_matrix"):
        assert forbidden not in source


def test_phase5a_documents_and_enforces_corrected_public_boundary() -> None:
    architecture = ARCHITECTURE.read_text(encoding="utf-8")
    contracts = (ROOT / "src/archaeoai/inference_system/contracts.py").read_text(encoding="utf-8")
    security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    correction = (ROOT / "research-log/2026-09-05-phase-5a-serialization-correction.md").read_text(
        encoding="utf-8"
    )

    assert "explicit eight-field allowlist" in architecture
    assert "controlled message codes with fixed rendering" in architecture
    assert "first contract revision" in architecture
    assert "class WarningCode(StrEnum)" in contracts
    assert "class LimitationCode(StrEnum)" in contracts
    assert "class ModelIdentifier(StrEnum)" in contracts
    assert "APPROVED_MODEL_CONFIG_SHA256" in contracts
    assert "warnings: tuple[str" not in contracts
    assert "limitations: tuple[str" not in contracts
    assert "approved controlled message codes" in security
    assert "Private request metadata must never be traversed" in security
    assert "Fictional probes demonstrated" in correction
    assert "did not load or execute a model" in correction
